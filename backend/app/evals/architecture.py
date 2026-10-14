"""Render the system architecture diagram, annotated with the latest eval metrics.

Usage (from backend/):  .venv/Scripts/python -m app.evals.architecture
The harness calls render_architecture() after every saved run, so the numbers in
the diagram always match the newest report.
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .harness import LATEST_PATH

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_PATHS = [REPO_ROOT / "docs" / "architecture.svg", REPO_ROOT / "frontend" / "public" / "architecture.svg"]

W, H = 1480, 1130
BG = "#0b1120"
PANEL = "#111a2e"
BOX = "#16213a"
INK = "#f1f5f9"
INK_2 = "#cbd5e1"
INK_3 = "#94a3b8"
LINE = "#64748b"
# Layer accents (identity only; all text stays in ink tokens).
CLIENT = "#3987e5"
SERVER = "#d95926"
DATA = "#199e70"
EXTERNAL = "#9085e9"
GOOD = "#34d399"
BAD = "#fb7185"

FONT = "font-family=\"Inter, 'Segoe UI', system-ui, sans-serif\""


class Svg:
    def __init__(self) -> None:
        self.parts: List[str] = []

    def add(self, markup: str) -> None:
        self.parts.append(markup)

    def rect(self, x, y, w, h, fill=BOX, stroke=None, rx=10, dash=False, width=1.5) -> None:
        stroke_attr = f' stroke="{stroke}" stroke-width="{width}"' if stroke else ""
        dash_attr = ' stroke-dasharray="6 5"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{stroke_attr}{dash_attr}/>')

    def text(self, x, y, content, size=12, color=INK_2, weight=400, anchor="start") -> None:
        self.add(
            f'<text x="{x}" y="{y}" {FONT} font-size="{size}" font-weight="{weight}" '
            f'fill="{color}" text-anchor="{anchor}">{escape(str(content))}</text>'
        )

    def lines(self, x, y, rows: Sequence[str], size=12, color=INK_2, gap=17) -> None:
        for index, row in enumerate(rows):
            self.text(x, y + index * gap, row, size=size, color=color)

    def arrow(self, points: Sequence[Tuple[float, float]], label: Optional[str] = None,
              label_at: Optional[Tuple[float, float]] = None, color=LINE, both=False, dash=False) -> None:
        path = " ".join(f"{'M' if i == 0 else 'L'}{x},{y}" for i, (x, y) in enumerate(points))
        start = ' marker-start="url(#arrow-start)"' if both else ""
        dash_attr = ' stroke-dasharray="5 4"' if dash else ""
        self.add(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.6"{dash_attr} marker-end="url(#arrow)"{start}/>')
        if label and label_at:
            lx, ly = label_at
            width = 7 * len(label) + 12
            self.add(f'<rect x="{lx - width / 2}" y="{ly - 12}" width="{width}" height="17" rx="4" fill="{BG}"/>')
            self.text(lx, ly, label, size=11, color=INK_3, anchor="middle")

    def component(self, x, y, w, h, title, rows: Sequence[str], accent, subtitle: Optional[str] = None) -> None:
        self.rect(x, y, w, h, fill=BOX, stroke="#26324d")
        self.add(f'<rect x="{x}" y="{y + 10}" width="3" height="{h - 20}" rx="1.5" fill="{accent}"/>')
        self.text(x + 14, y + 22, title, size=13, color=INK, weight=600)
        offset = 40
        if subtitle:
            self.text(x + 14, y + 38, subtitle, size=11, color=INK_3)
            offset = 56
        self.lines(x + 14, y + offset, rows, size=12)

    def layer(self, x, y, w, h, title, accent, note: Optional[str] = None) -> None:
        self.rect(x, y, w, h, fill=PANEL, stroke=accent, rx=14, width=1.2, dash=True)
        self.text(x + 16, y + 24, title, size=14, color=INK, weight=700)
        if note:
            self.text(x + w - 16, y + 24, note, size=11, color=INK_3, anchor="end")

    def render(self) -> str:
        defs = (
            "<defs>"
            f'<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker>'
            f'<marker id="arrow-start" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker>'
            "</defs>"
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-labelledby="title desc"><title id="title">AI PDF Reader architecture</title>'
            f'<desc id="desc">React frontend, FastAPI backend with ingestion, hybrid retrieval and generation, '
            f'Supabase data plane and external AI services, annotated with RAG eval metrics.</desc>'
            f'{defs}<rect width="{W}" height="{H}" fill="{BG}"/>' + "".join(self.parts) + "</svg>"
        )


def _pct(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{round(value * 100)}%"


def _num(value: Optional[float], digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def _ms(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{round(value)} ms"


def build_svg(report: Optional[Dict[str, Any]]) -> str:
    variants = (report or {}).get("variants", {})
    hybrid = variants.get("hybrid", {}).get("summary", {})
    dense = variants.get("dense", {}).get("summary", {})
    rerank = variants.get("hybrid_rerank", {}).get("summary", {})
    cross = variants.get("cross_document", {}).get("summary", {})
    ingest = (report or {}).get("ingest", {})
    gates = (report or {}).get("gates", [])

    svg = Svg()
    svg.text(40, 46, "AI PDF Reader · system architecture", size=24, color=INK, weight=700)
    svg.text(40, 70, "Upload PDFs, read them with related passages from your other PDFs, chat, insights and podcasts, grounded by hybrid RAG.",
             size=13, color=INK_3)

    # ---------------------------------------------------------------- client layer
    svg.layer(40, 92, 1000, 196, "Client · React 18 + Vite SPA", CLIENT, "Vercel (prod) · localhost:5173 (dev)")
    svg.component(60, 128, 230, 144, "Pages (react-router)", [
        "Landing, Login, Signup",
        "Forgot / Reset password",
        "Library (upload, manage)",
        "Reader /reader/:id?page=N",
        "Evals (this report)",
    ], CLIENT)
    svg.component(306, 128, 230, 144, "State (contexts)", [
        "AuthContext: Supabase",
        "  session, recovery flow",
        "PDFContext: documents,",
        "  related sections, insights",
        "  (stale responses dropped)",
    ], CLIENT)
    svg.component(552, 128, 230, 144, "Reader UI", [
        "react-pdf viewer (auth bytes)",
        "Related-PDFs side panel",
        "Chatbot (docked / floating)",
        "Insights + podcast modal",
        "Text-selection → Ask LLM",
    ], CLIENT)
    svg.component(798, 128, 226, 144, "Transport", [
        "REST + Bearer JWT",
        "  VITE_API_URL",
        "WebSocket /ws/{client_id}",
        "  upload progress",
        "supabase-js for auth only",
    ], CLIENT)

    # Supabase Auth (external to the right of client)
    svg.layer(1070, 92, 370, 196, "Supabase Auth", EXTERNAL, "project ai-pdf-reader")
    svg.component(1090, 128, 330, 144, "GoTrue", [
        "Email + password sign-in / sign-up",
        "Password-reset email → /reset-password",
        "Issues ES256 access tokens",
        "Publishes JWKS for verification",
        "Redirect allow-list: localhost:5173/**",
    ], EXTERNAL)
    svg.arrow([(1024, 200), (1088, 200)], "auth", (1057, 192), both=True)

    # ---------------------------------------------------------------- backend layer
    svg.layer(40, 318, 1000, 514, "Backend · FastAPI (Docker on Render · uvicorn :8000 locally)", SERVER, "app/main.py")
    svg.component(60, 354, 648, 170, "API routes", [
        "Upload: /upload/active_file · /upload/context_files  (SHA-256 duplicate check)",
        "Library: /api/documents[/{id}] · /api/files/{name} · /api/library/statistics",
        "Side panel: /api/recommendations/{id}  (open PDF excluded, relevance floor)",
        "AI: /api/chat · /api/chat/sessions · /api/insights/{id} · /api/highlights/{id}",
        "      /api/text-selection-analysis · /api/ask-gpt · /api/ask-gemini-selection",
        "Media / PDF tools: /api/generate-podcast · /api/audio/{name} · split · merge",
        "Ops: /api/rag/process/{id} · /api/evals/* · /healthz · /config · /ws/{client_id}",
    ], SERVER)
    svg.component(724, 354, 300, 170, "Auth middleware", [
        "Verify JWT via Supabase JWKS",
        "  (ES256; HS256 secret fallback)",
        "Every DB query scoped by user_id",
        "Dev-only bypass: APP_ENV=development",
        "  + AUTH_BYPASS_ENABLED=true",
    ], SERVER)
    svg.arrow([(722, 410), (710, 410)])

    svg.component(60, 540, 300, 276, "Ingestion", [
        "Active upload: sections from the",
        "  PDF outline / headings (PyMuPDF),",
        "  per-page fallback",
        "Context upload: multi-PDF sections",
        "  (IntelligentPDFBrain)",
        f"Split: {ingest.get('chunk_size', 1000)} chars, {ingest.get('chunk_overlap', 200)} overlap, ≥100 min",
        "Embed text = doc + page +",
        "  section title + chunk",
        "NVIDIA batch embed (passage)",
        "  → store chunk + vector",
        "",
        f"eval: {_num(ingest.get('embedding_ms_per_chunk'), 1)} ms / chunk embedded",
    ], SERVER)
    svg.component(376, 540, 330, 276, "Hybrid retrieval  (rag_service)", [
        "Chat only: LLM rewrites the query",
        "1. Embed query (NVIDIA, query mode)",
        "2. Vector kNN + Postgres FTS",
        "3. Merge candidates by chunk id",
        "4. Score = 0.8·vector + 0.2·BM25",
        "     (+recency for 'latest' queries)",
        "5. Chat only: NVIDIA rerank",
        "6. Semantic cache (exact + ≥0.97 cos)",
        "Side panel: open PDF excluded, persona",
        f"  re-score if set, score ≥ {_num(cross.get('min_score'))}",
        "",
        f"eval p50 {_ms(hybrid.get('latency_p50_ms'))} · p95 {_ms(hybrid.get('latency_p95_ms'))}",
        f"rerank p95 {_ms(rerank.get('latency_p95_ms'))}",
    ], SERVER)
    svg.component(722, 540, 302, 276, "Generation & media", [
        "LLM (LLM_PROVIDER):",
        "  Gemini 2.5 Flash (default)",
        "  Azure OpenAI · OpenAI · Ollama",
        "Chat: PDF context + RAG chunks",
        "  labelled [Page N]",
        "Insights: takeaways, did-you-know,",
        "  counterpoints, tips, deep dives",
        "Podcast: templated script (no LLM),",
        "  ≤1000 chars → Azure Speech TTS",
        "Chat history: SQLite file",
        "  (not in Supabase; lost on redeploy)",
    ], SERVER)
    svg.arrow([(210, 524), (210, 538)])
    svg.arrow([(540, 524), (540, 538)])
    svg.arrow([(680, 524), (680, 532), (870, 532), (870, 538)])
    svg.arrow([(706, 660), (720, 660)])

    # client → backend
    svg.arrow([(540, 288), (540, 352)], "HTTPS + JWT / WS", (540, 322), both=True)
    # auth middleware → Supabase JWKS
    svg.arrow([(1024, 410), (1060, 410), (1060, 290)], "JWKS", (1060, 306), dash=True)

    # ---------------------------------------------------------------- data + external
    svg.layer(40, 862, 640, 236, "Data plane · Supabase (default)", DATA)
    svg.component(60, 898, 300, 184, "Postgres + pgvector", [
        "documents (RLS: owner only)",
        f"document_chunks: vector({ingest.get('embedding_dimension', 2048)})",
        "  + GIN full-text index",
        "HNSW on halfvec cast (cosine)",
        "RPC match_document_chunks",
        "  (open PDF excluded before LIMIT)",
        "RPC search_document_chunks_fts",
    ], DATA)
    svg.component(376, 898, 288, 184, "Storage + local fallback", [
        "Private bucket 'documents'",
        "  user_id/doc_id/file.pdf, 100 MB",
        "",
        "PERSISTENCE_BACKEND=sqlite:",
        "  SQLite + FTS5 BM25",
        "  FAISS HNSW (M=32) vectors",
        "  PDFs on local disk",
    ], DATA)

    svg.layer(700, 862, 340, 236, "External AI services", EXTERNAL)
    svg.component(720, 898, 300, 184, "NVIDIA · Google · Azure", [
        "NVIDIA embeddings:",
        f"  {ingest.get('embedding_model', 'nvidia/nemotron-3-embed-1b')}",
        "NVIDIA reranker:",
        f"  {((report or {}).get('config') or {}).get('reranker_model', 'nvidia/llama-nemotron-rerank-vl-1b-v2').replace('nvidia/', '')}",
        "Google Gemini API (LLM)",
        "Azure Speech (TTS)",
    ], EXTERNAL)

    svg.arrow([(275, 816), (275, 896)], "chunks + vectors", (275, 846))
    svg.arrow([(345, 816), (345, 836), (600, 836), (600, 896)], "PDF file", (600, 872), dash=True)
    svg.arrow([(470, 816), (470, 896)], "kNN + FTS RPCs", (470, 856), both=True)
    svg.arrow([(690, 816), (690, 846), (870, 846), (870, 896)], "embed / rerank", (780, 850))
    svg.arrow([(960, 816), (960, 896)], "LLM / TTS", (960, 856))

    # ---------------------------------------------------------------- metrics panel
    svg.rect(1070, 318, 370, 780, fill=PANEL, stroke="#334155", rx=14, width=1.2)
    svg.text(1090, 346, "RAG eval metrics", size=16, color=INK, weight=700)
    if report:
        svg.text(1090, 366, f"run {report.get('run_id')} · {report.get('mode')} models", size=11, color=INK_3)
        dataset = report.get("dataset", {})
        svg.text(1090, 383, f"{dataset.get('queries')} queries · {len(dataset.get('documents', []))} PDFs · "
                            f"{dataset.get('cross_document_cases')} side-panel cases", size=11, color=INK_3)
    else:
        svg.text(1090, 366, "No eval report yet: run python -m app.evals.harness", size=11, color=BAD)

    def metric_table(top: int, title: str, rows: List[Tuple[str, str]]) -> int:
        svg.text(1090, top, title, size=12, color=INK, weight=600)
        y = top + 22
        for label, value in rows:
            svg.text(1102, y, label, size=12, color=INK_2)
            svg.text(1420, y, value, size=12, color=INK, weight=600, anchor="end")
            y += 19
        return y + 10

    y = metric_table(414, "Retrieval quality (dense → hybrid → +rerank)", [
        ("Hit@1", f"{_pct(dense.get('hit@1'))} → {_pct(hybrid.get('hit@1'))} → {_pct(rerank.get('hit@1'))}"),
        ("Hit@3", f"{_pct(dense.get('hit@3'))} → {_pct(hybrid.get('hit@3'))} → {_pct(rerank.get('hit@3'))}"),
        ("MRR", f"{_num(dense.get('mrr'))} → {_num(hybrid.get('mrr'))} → {_num(rerank.get('mrr'))}"),
        ("nDCG@5", f"{_num(dense.get('ndcg@5'))} → {_num(hybrid.get('ndcg@5'))} → {_num(rerank.get('ndcg@5'))}"),
        ("Answer-term recall", f"{_pct(hybrid.get('answer_term_recall'))} (hybrid)"),
    ])
    y = metric_table(y, "Side panel (cross-PDF recommendations)", [
        ("Hit@3", _pct(cross.get("cross_doc_hit@3"))),
        ("MRR", _num(cross.get("cross_doc_mrr"))),
        ("Open-PDF leakage", _pct(cross.get("cross_doc_leakage"))),
        ("Off-topic results", _pct(cross.get("cross_doc_off_topic"))),
        ("Avg matches shown (max 3)", _num(cross.get("cross_doc_avg_shown"), 1)),
        ("Relevance floor", f"≥ {_num(cross.get('min_score'))}"),
        ("Empty panels", _pct(cross.get("cross_doc_empty_rate"))),
    ])
    y = metric_table(y, "Latency (incl. hosted query embedding)", [
        ("Hybrid p50 / p95", f"{_ms(hybrid.get('latency_p50_ms'))} / {_ms(hybrid.get('latency_p95_ms'))}"),
        ("+ rerank p50 / p95", f"{_ms(rerank.get('latency_p50_ms'))} / {_ms(rerank.get('latency_p95_ms'))}"),
        ("Side panel p95", _ms(cross.get("latency_p95_ms"))),
    ])

    svg.text(1090, y, "Quality gates", size=12, color=INK, weight=600)
    y += 22
    for gate in gates:
        passed = gate.get("passed")
        svg.add(f'<circle cx="{1106}" cy="{y - 4}" r="5" fill="{GOOD if passed else BAD}"/>')
        label = f"{gate['variant'].replace('_', ' ')} {gate['metric'].replace('cross_doc_', '')} {gate['op']} {gate['threshold']}"
        svg.text(1118, y, label, size=11, color=INK_2)
        svg.text(1420, y, "PASS" if passed else "FAIL", size=11, color=GOOD if passed else BAD, weight=700, anchor="end")
        y += 18
    if report:
        overall = "All gates pass" if report.get("passed") else "Gates failing"
        svg.text(1090, y + 12, overall, size=13, color=GOOD if report.get("passed") else BAD, weight=700)

    svg.text(40, H - 8, "Generated by backend/app/evals/architecture.py from app/evals/results/latest.json",
             size=10, color=INK_3)
    return svg.render()


def render_architecture(report: Optional[Dict[str, Any]] = None) -> List[Path]:
    if report is None and LATEST_PATH.exists():
        report = json.loads(LATEST_PATH.read_text(encoding="utf-8"))
    markup = build_svg(report)
    written = []
    for path in OUTPUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markup, encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    for written_path in render_architecture():
        print(f"Wrote {written_path}")
