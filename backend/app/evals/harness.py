"""RAG evaluation harness.

Runs the production retrieval code (chunker, embedding text strategy, FAISS
vector store, SQLite FTS5 BM25, hybrid score fusion, NVIDIA reranking) against a
hand-labelled corpus in fully isolated temporary stores, then writes a JSON
report the API serves to the Evals page.

Usage (from backend/):
    .venv/Scripts/python -m app.evals.harness            # live NVIDIA embeddings
    .venv/Scripts/python -m app.evals.harness --offline  # deterministic, no network
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import metrics as m

EVALS_DIR = Path(__file__).resolve().parent
DATASET_PATH = EVALS_DIR / "dataset.json"
RESULTS_DIR = EVALS_DIR / "results"
LATEST_PATH = RESULTS_DIR / "latest.json"
HISTORY_DIR = RESULTS_DIR / "history"

EVAL_USER_ID = "00000000-0000-4000-8000-0000000e7a15"
TOP_K = 5
CROSS_DOC_TOP_K = 3  # the side panel shows three matches

# Release gates: a run "passes" only when every gate holds.
QUALITY_GATES: List[Dict[str, Any]] = [
    {"metric": "hit@3", "variant": "hybrid", "op": ">=", "threshold": 0.80,
     "why": "Recommendations and chat use the hybrid path; the right page should be in the top 3."},
    {"metric": "mrr", "variant": "hybrid", "op": ">=", "threshold": 0.65,
     "why": "The best page should usually be first or second."},
    {"metric": "answer_term_recall", "variant": "hybrid", "op": ">=", "threshold": 0.75,
     "why": "Retrieved context must contain the facts the answer needs."},
    {"metric": "cross_doc_hit@3", "variant": "cross_document", "op": ">=", "threshold": 0.80,
     "why": "The side panel should surface the related page from another PDF."},
    {"metric": "cross_doc_leakage", "variant": "cross_document", "op": "<=", "threshold": 0.0,
     "why": "The side panel must never show the PDF that is already open."},
    {"metric": "cross_doc_off_topic", "variant": "cross_document", "op": "<=", "threshold": 0.25,
     "why": "Side-panel matches should come from related subjects, not unrelated filler."},
    {"metric": "latency_p95_ms", "variant": "hybrid", "op": "<=", "threshold": 2500,
     "why": "Page turns refresh the panel; retrieval must stay interactive."},
]


class LexicalHashEmbedder:
    """Deterministic offline embedder (hashed unigrams + bigrams).

    Used with --offline so the harness runs without network access or cost.
    Its scores measure the pipeline mechanics, not NVIDIA model quality, and
    reports are labelled accordingly.
    """

    model_name = "offline/lexical-hash-v1"

    def __init__(self, dimension: int):
        self.embedding_dim = dimension

    def _vector(self, text: str) -> List[float]:
        tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        vector = [0.0] * self.embedding_dim
        for feature in features:
            digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.embedding_dim
            vector[index] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def generate_embedding(self, text: str, input_type: str = "query") -> List[float]:
        return self._vector(text)

    def generate_embeddings_batch(self, texts: Sequence[str], batch_size: int = 32,
                                  show_progress: bool = False, input_type: str = "passage") -> List[List[float]]:
        return [self._vector(text) for text in texts]


class DisabledReranker:
    """Stand-in that makes rerank_results fall back to fused ranking."""

    def rerank(self, query, passages):
        from ..reranker_service import RerankerServiceUnavailableError

        raise RerankerServiceUnavailableError("reranking disabled for this run")


@dataclass
class Corpus:
    rag: Any
    pages: Dict[tuple, str]
    names: Dict[str, str]
    topics: Dict[str, str]
    ingest: Dict[str, Any]


def _git_commit() -> Optional[str]:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
            cwd=EVALS_DIR, timeout=5, check=True,
        ).stdout.strip() or None
    except Exception:
        return None


def build_corpus(dataset: Dict[str, Any], workdir: Path, offline: bool) -> Corpus:
    """Ingest the eval corpus with production code into isolated stores."""
    from ..chunking_service import ChunkingService
    from ..database import DocumentDatabase
    from ..ingestion_service import DocumentIngestionService
    from ..nvidia_retrieval_config import load_nvidia_embedding_config
    from ..rag_service import RAGService
    from ..semantic_cache import SemanticSearchCache
    from ..vector_store import FAISSVectorStore

    dimension = load_nvidia_embedding_config().dimension
    if offline:
        embedder = LexicalHashEmbedder(dimension)
        reranker = DisabledReranker()
    else:
        from ..embedding_service import get_embedding_service
        from ..reranker_service import get_reranker_service

        embedder = get_embedding_service()
        reranker = get_reranker_service()

    database = DocumentDatabase(db_path=str(workdir / "eval.db"))
    vector_store = FAISSVectorStore(
        str(workdir / "faiss.bin"), str(workdir / "faiss-meta.json"), dimension=dimension
    )
    chunker = ChunkingService()
    # Reuse the production embedding-text and vector-metadata strategy.
    ingestion = DocumentIngestionService.__new__(DocumentIngestionService)
    ingestion.embedding_service = embedder

    pages: Dict[tuple, str] = {}
    names: Dict[str, str] = {}
    all_chunks, owners = [], []
    started = time.perf_counter()
    for spec in dataset["documents"]:
        document = database.create_document(
            filename=spec["name"], original_name=spec["name"], file_size=0,
            file_path=f"eval://{spec['id']}", client_id=EVAL_USER_ID, document_id=spec["id"],
        )
        names[spec["id"]] = spec["name"]
        for page_number, text in enumerate(spec["pages"], start=1):
            pages[(spec["id"], page_number)] = text
            chunks = chunker._split_text(
                text=text, page_number=page_number, document_id=spec["id"],
                start_index=len(all_chunks),
                base_metadata={
                    "document_name": spec["name"], "filename": spec["name"],
                    "section_title": f"Page {page_number}", "source_algorithm": "eval",
                },
            )
            all_chunks.extend(chunks)
            owners.extend([document] * len(chunks))
    chunk_seconds = time.perf_counter() - started

    texts = [ingestion._embedding_text(doc, chunk) for doc, chunk in zip(owners, all_chunks)]
    started = time.perf_counter()
    embeddings = embedder.generate_embeddings_batch(texts, batch_size=32)
    embed_seconds = time.perf_counter() - started

    metadatas = []
    for document, chunk, embedding in zip(owners, all_chunks, embeddings):
        chunk_id = f"{chunk.document_id}-c{chunk.chunk_index}"
        metadata = ingestion._vector_metadata(document=document, user_id=EVAL_USER_ID, chunk=chunk, chunk_id=chunk_id)
        metadatas.append(metadata)
        database.store_chunk(
            document_id=chunk.document_id, chunk_text=chunk.text, chunk_index=chunk.chunk_index,
            page_number=chunk.page_number, client_id=EVAL_USER_ID, chunk_id=chunk_id,
            char_count=chunk.metadata.get("char_count"), word_count=chunk.metadata.get("word_count"),
        )
    vector_store.add_documents(embeddings, metadatas)

    rag = RAGService.__new__(RAGService)
    rag.embedding_service = embedder
    rag.vector_store = vector_store
    rag.reranker = reranker
    rag.semantic_cache = SemanticSearchCache()
    rag.chunk_search_db = database

    chunk_lengths = [len(chunk.text) for chunk in all_chunks]
    return Corpus(
        rag=rag, pages=pages, names=names,
        topics={spec["id"]: spec.get("topic", spec["id"]) for spec in dataset["documents"]},
        ingest={
            "documents": len(dataset["documents"]),
            "pages": len(pages),
            "chunks": len(all_chunks),
            "avg_chunk_chars": round(m.mean(chunk_lengths), 1),
            "max_chunk_chars": max(chunk_lengths, default=0),
            "chunk_size": chunker.chunk_size,
            "chunk_overlap": chunker.chunk_overlap,
            "embedding_model": getattr(embedder, "model_name", "unknown"),
            "embedding_dimension": dimension,
            "chunking_ms": round(chunk_seconds * 1000, 1),
            "embedding_ms": round(embed_seconds * 1000, 1),
            "embedding_ms_per_chunk": round(embed_seconds * 1000 / max(len(all_chunks), 1), 1),
        },
    )


def _page_keys(results) -> List[tuple]:
    return m.dedupe_pages((r.document_id, int(r.page_number)) for r in results)


async def _run_variant(corpus: Corpus, queries: List[Dict[str, Any]], name: str,
                       search: Callable[[str], Any]) -> Dict[str, Any]:
    corpus.rag.semantic_cache.clear()
    per_query, latencies = [], []
    reranked_any = False
    for item in queries:
        relevant = {(doc, int(page)) for doc, page in item["relevant"]}
        started = time.perf_counter()
        results = await search(item["query"])
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)
        reranked_any = reranked_any or any(
            (r.metadata or {}).get("rerank_score") is not None for r in results
        )
        ranked = _page_keys(results)
        context = " ".join(r.chunk_text for r in results[:3])
        per_query.append({
            "id": item["id"], "category": item["category"], "query": item["query"],
            "relevant": [list(key) for key in sorted(relevant)],
            "retrieved": [list(key) for key in ranked[:TOP_K]],
            "hit@1": m.hit_at_k(ranked, relevant, 1),
            "hit@3": m.hit_at_k(ranked, relevant, 3),
            "hit@5": m.hit_at_k(ranked, relevant, 5),
            "recall@5": m.recall_at_k(ranked, relevant, 5),
            "precision@3": m.precision_at_k(ranked, relevant, 3),
            "mrr": m.reciprocal_rank(ranked, relevant, TOP_K),
            "ndcg@5": m.ndcg_at_k(ranked, relevant, 5),
            "answer_term_recall": m.answer_term_recall(context, item.get("answer_terms", [])),
            "latency_ms": round(latency_ms, 1),
        })
    return {
        "name": name,
        "reranker_applied": reranked_any,
        "summary": _summarise(per_query, latencies),
        "by_category": {
            category: _summarise([q for q in per_query if q["category"] == category],
                                 [q["latency_ms"] for q in per_query if q["category"] == category])
            for category in sorted({q["category"] for q in per_query})
        },
        "queries": per_query,
    }


def _summarise(rows: List[Dict[str, Any]], latencies: List[float]) -> Dict[str, float]:
    keys = ["hit@1", "hit@3", "hit@5", "recall@5", "precision@3", "mrr", "ndcg@5", "answer_term_recall"]
    summary = {key: round(m.mean([row[key] for row in rows]), 4) for key in keys}
    summary["queries"] = len(rows)
    summary["latency_p50_ms"] = round(m.percentile(latencies, 50), 1)
    summary["latency_p95_ms"] = round(m.percentile(latencies, 95), 1)
    return summary


async def _run_cross_document(corpus: Corpus, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Mirror /api/recommendations: current page text as query, open PDF excluded,
    weak matches below the side panel's relevance floor dropped."""
    from ..rag_service import CROSS_DOCUMENT_MIN_SCORE

    corpus.rag.semantic_cache.clear()
    rows, latencies = [], []
    for case in cases:
        source = (case["source"][0], int(case["source"][1]))
        relevant = {(doc, int(page)) for doc, page in case["relevant"]}
        started = time.perf_counter()
        results = await corpus.rag.search_documents(
            query=corpus.pages[source][:2000], top_k=CROSS_DOC_TOP_K,
            exclude_document_id=source[0], user_id=EVAL_USER_ID, use_advanced_rag=False,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)
        results = [
            r for r in results
            if ((r.metadata or {}).get("retrieval_score") or 0.0) >= CROSS_DOCUMENT_MIN_SCORE
        ]
        ranked = _page_keys(results)
        leaked = sum(1 for r in results if r.document_id == source[0])
        off_topic = sum(1 for r in results if corpus.topics.get(r.document_id) != corpus.topics[source[0]])
        rows.append({
            "id": case["id"], "source": list(source),
            "source_name": corpus.names[source[0]],
            "relevant": [list(key) for key in sorted(relevant)],
            "retrieved": [list(key) for key in ranked],
            "hit@1": m.hit_at_k(ranked, relevant, 1),
            "hit@3": m.hit_at_k(ranked, relevant, CROSS_DOC_TOP_K),
            "mrr": m.reciprocal_rank(ranked, relevant, CROSS_DOC_TOP_K),
            "leakage": leaked / len(results) if results else 0.0,
            "off_topic": off_topic / len(results) if results else 0.0,
            "shown": len(results),
            "empty": 0.0 if results else 1.0,
            "latency_ms": round(latency_ms, 1),
        })
    return {
        "name": "cross_document",
        "summary": {
            "cases": len(rows),
            "cross_doc_hit@1": round(m.mean([r["hit@1"] for r in rows]), 4),
            "cross_doc_hit@3": round(m.mean([r["hit@3"] for r in rows]), 4),
            "cross_doc_mrr": round(m.mean([r["mrr"] for r in rows]), 4),
            "cross_doc_leakage": round(m.mean([r["leakage"] for r in rows]), 4),
            "cross_doc_off_topic": round(m.mean([r["off_topic"] for r in rows]), 4),
            "cross_doc_avg_shown": round(m.mean([r["shown"] for r in rows]), 2),
            "min_score": CROSS_DOCUMENT_MIN_SCORE,
            "cross_doc_empty_rate": round(m.mean([r["empty"] for r in rows]), 4),
            "latency_p50_ms": round(m.percentile(latencies, 50), 1),
            "latency_p95_ms": round(m.percentile(latencies, 95), 1),
        },
        "cases": rows,
    }


def _evaluate_gates(variants: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    evaluated = []
    for gate in QUALITY_GATES:
        value = variants.get(gate["variant"], {}).get("summary", {}).get(gate["metric"])
        passed = value is not None and (
            value >= gate["threshold"] if gate["op"] == ">=" else value <= gate["threshold"]
        )
        evaluated.append({**gate, "value": value, "passed": bool(passed)})
    return evaluated


async def run(offline: bool) -> Dict[str, Any]:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    # ignore_cleanup_errors: sqlite3 context managers commit but do not close,
    # so Windows can still hold the temp DB open when the directory is removed.
    with tempfile.TemporaryDirectory(prefix="rag-evals-", ignore_cleanup_errors=True) as tmp:
        corpus = build_corpus(dataset, Path(tmp), offline=offline)
        rag, queries = corpus.rag, dataset["queries"]

        async def dense(query):
            embedding = rag.embedding_service.generate_embedding(query)
            return rag.vector_store.search_similar(embedding, top_k=TOP_K, user_id=EVAL_USER_ID)

        async def hybrid(query):
            return await rag.search_documents(query=query, top_k=TOP_K, user_id=EVAL_USER_ID,
                                              use_advanced_rag=False)

        async def hybrid_rerank(query):
            return await rag.search_documents(query=query, top_k=TOP_K, user_id=EVAL_USER_ID,
                                              use_advanced_rag=True, llm_provider=None)

        variants = {
            "dense": await _run_variant(corpus, queries, "dense", dense),
            "hybrid": await _run_variant(corpus, queries, "hybrid", hybrid),
            "hybrid_rerank": await _run_variant(corpus, queries, "hybrid_rerank", hybrid_rerank),
            "cross_document": await _run_cross_document(corpus, dataset["cross_document"]),
        }
        ingest = corpus.ingest

    gates = _evaluate_gates(variants)
    return {
        "schema_version": 1,
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "offline" if offline else "live",
        "git_commit": _git_commit(),
        "python": platform.python_version(),
        "dataset": {
            "name": dataset["name"], "description": dataset["description"],
            "documents": [{"id": d["id"], "name": d["name"], "pages": len(d["pages"])} for d in dataset["documents"]],
            "queries": len(queries), "cross_document_cases": len(dataset["cross_document"]),
            "categories": sorted({q["category"] for q in queries}),
        },
        "config": {
            "top_k": TOP_K, "cross_document_top_k": CROSS_DOC_TOP_K,
            "fusion_weights": {"vector": 0.8, "keyword": 0.2},
            "reranker_model": os.getenv("NVIDIA_RERANK_MODEL") or _default_rerank_model(),
        },
        "ingest": ingest,
        "variants": variants,
        "gates": gates,
        "passed": all(gate["passed"] for gate in gates),
    }


def _default_rerank_model() -> str:
    from ..nvidia_retrieval_config import DEFAULT_RERANK_MODEL

    return DEFAULT_RERANK_MODEL


def save(report: Dict[str, Any]) -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2)
    LATEST_PATH.write_text(payload, encoding="utf-8")
    history_path = HISTORY_DIR / f"{report['run_id']}-{report['mode']}.json"
    history_path.write_text(payload, encoding="utf-8")
    return history_path


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root_env = EVALS_DIR.parents[2] / ".env"
    if root_env.exists():
        load_dotenv(root_env)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RAG retrieval evals")
    parser.add_argument("--offline", action="store_true", help="use the deterministic offline embedder")
    parser.add_argument("--no-save", action="store_true", help="print the summary without writing results")
    args = parser.parse_args()
    _load_env()

    pipeline_log = io.StringIO()
    # The pipeline prints per-query diagnostics; keep the CLI output to the summary.
    with contextlib.redirect_stdout(pipeline_log):
        report = asyncio.run(run(offline=args.offline))
    if not args.no_save:
        print(f"Saved {save(report)}")
        # Keep the architecture diagram's metrics in sync with the newest run.
        from .architecture import render_architecture

        for path in render_architecture(report):
            print(f"Updated {path}")
    for name, variant in report["variants"].items():
        summary = variant["summary"]
        shown = {k: v for k, v in summary.items() if k not in ("queries", "cases")}
        print(f"{name:15s} {shown}")
    for gate in report["gates"]:
        mark = "PASS" if gate["passed"] else "FAIL"
        print(f"[{mark}] {gate['variant']}.{gate['metric']} {gate['op']} {gate['threshold']} (got {gate['value']})")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
