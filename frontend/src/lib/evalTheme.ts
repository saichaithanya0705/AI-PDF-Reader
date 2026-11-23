// Editorial light-surface categorical palette:
// One accent (vermilion) leads for the primary production hybrid variant;
// neutral slate and deep pine distinguish baseline and reranked variants.
export const VARIANT_COLORS: Record<string, string> = {
  dense: '#78746c',
  hybrid: '#c23b22',
  hybrid_rerank: '#1d6f5f',
};

export const VARIANT_LABELS: Record<string, string> = {
  dense: 'Dense (vector only)',
  hybrid: 'Hybrid (vector + BM25)',
  hybrid_rerank: 'Hybrid + NVIDIA rerank',
};

export const RETRIEVAL_VARIANTS = ['dense', 'hybrid', 'hybrid_rerank'] as const;
