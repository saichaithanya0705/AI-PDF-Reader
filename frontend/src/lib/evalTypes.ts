// Mirrors the report written by backend/app/evals/harness.py (schema_version 1).
export type PageRef = [string, number];

export interface RetrievalSummary {
  'hit@1': number;
  'hit@3': number;
  'hit@5': number;
  'recall@5': number;
  'precision@3': number;
  mrr: number;
  'ndcg@5': number;
  answer_term_recall: number;
  queries: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
}

export interface QueryResult {
  id: string;
  category: string;
  query: string;
  relevant: PageRef[];
  retrieved: PageRef[];
  'hit@1': number;
  'hit@3': number;
  mrr: number;
  'ndcg@5': number;
  answer_term_recall: number;
  latency_ms: number;
}

export interface RetrievalVariant {
  name: string;
  reranker_applied: boolean;
  summary: RetrievalSummary;
  by_category: Record<string, RetrievalSummary>;
  queries: QueryResult[];
}

export interface CrossDocumentCase {
  id: string;
  source: PageRef;
  source_name: string;
  relevant: PageRef[];
  retrieved: PageRef[];
  'hit@1': number;
  'hit@3': number;
  mrr: number;
  leakage: number;
  off_topic: number;
  shown: number;
  latency_ms: number;
}

export interface CrossDocumentVariant {
  name: 'cross_document';
  summary: {
    cases: number;
    'cross_doc_hit@1': number;
    'cross_doc_hit@3': number;
    cross_doc_mrr: number;
    cross_doc_leakage: number;
    cross_doc_off_topic: number;
    cross_doc_avg_shown: number;
    min_score: number;
    cross_doc_empty_rate: number;
    latency_p50_ms: number;
    latency_p95_ms: number;
  };
  cases: CrossDocumentCase[];
}

export interface QualityGate {
  metric: string;
  variant: string;
  op: '>=' | '<=';
  threshold: number;
  why: string;
  value: number | null;
  passed: boolean;
}

export interface EvalReport {
  schema_version: number;
  run_id: string;
  created_at: string;
  mode: 'live' | 'offline';
  git_commit: string | null;
  dataset: {
    name: string;
    description: string;
    documents: { id: string; name: string; pages: number }[];
    queries: number;
    cross_document_cases: number;
    categories: string[];
  };
  config: {
    top_k: number;
    cross_document_top_k: number;
    fusion_weights: { vector: number; keyword: number };
    reranker_model: string;
  };
  ingest: {
    documents: number;
    pages: number;
    chunks: number;
    avg_chunk_chars: number;
    chunk_size: number;
    chunk_overlap: number;
    embedding_model: string;
    embedding_dimension: number;
    embedding_ms_per_chunk: number;
  };
  variants: {
    dense: RetrievalVariant;
    hybrid: RetrievalVariant;
    hybrid_rerank: RetrievalVariant;
    cross_document: CrossDocumentVariant;
  };
  gates: QualityGate[];
  passed: boolean;
}

export interface EvalHistoryEntry {
  run_id: string;
  created_at: string;
  mode: 'live' | 'offline';
  git_commit: string | null;
  passed: boolean;
  hybrid: Partial<RetrievalSummary>;
  hybrid_rerank: Partial<RetrievalSummary>;
  cross_document: Partial<CrossDocumentVariant['summary']>;
}
