import xml.dom.minidom

from backend.app.evals.architecture import build_svg


def _report(passed=True):
    summary = {"hit@1": 0.9, "hit@3": 1.0, "mrr": 0.95, "ndcg@5": 0.97, "answer_term_recall": 1.0,
               "latency_p50_ms": 300.0, "latency_p95_ms": 330.0}
    return {
        "run_id": "20261013T000000Z", "mode": "live", "passed": passed,
        "dataset": {"queries": 24, "documents": [{}, {}], "cross_document_cases": 6},
        "config": {"reranker_model": "nvidia/<rerank & model>"},
        "ingest": {"chunk_size": 1000, "chunk_overlap": 200, "embedding_dimension": 2048,
                   "embedding_model": "nvidia/nemotron-3-embed-1b", "embedding_ms_per_chunk": 100.0},
        "variants": {
            "dense": {"summary": summary}, "hybrid": {"summary": summary}, "hybrid_rerank": {"summary": summary},
            "cross_document": {"summary": {"cross_doc_hit@3": 0.83, "cross_doc_mrr": 0.83,
                                           "cross_doc_leakage": 0.0, "cross_doc_empty_rate": 0.0,
                                           "latency_p95_ms": 320.0}},
        },
        "gates": [{"metric": "mrr", "variant": "hybrid", "op": ">=", "threshold": 0.65, "passed": passed}],
    }


def test_svg_is_valid_xml_and_shows_report_metrics():
    markup = build_svg(_report())
    xml.dom.minidom.parseString(markup)  # raises if escaping is broken
    assert "20261013T000000Z" in markup
    assert "0.95" in markup and "83%" in markup
    assert "All gates pass" in markup
    assert "&lt;rerank &amp; model&gt;" in markup


def test_svg_renders_without_a_report():
    markup = build_svg(None)
    xml.dom.minidom.parseString(markup)
    assert "No eval report yet" in markup
