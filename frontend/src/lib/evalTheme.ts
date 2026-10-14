// Categorical slots 1-3 (dark steps), validated on the slate-900 surface with the
// dataviz palette checker: worst adjacent CVD ΔE 9.4, normal-vision ΔE 26.5,
// all >= 3:1 contrast. Colour follows the variant, never its rank.
export const VARIANT_COLORS: Record<string, string> = {
  dense: '#3987e5',
  hybrid: '#d95926',
  hybrid_rerank: '#199e70',
};

export const VARIANT_LABELS: Record<string, string> = {
  dense: 'Dense (vector only)',
  hybrid: 'Hybrid (vector + BM25)',
  hybrid_rerank: 'Hybrid + NVIDIA rerank',
};

export const RETRIEVAL_VARIANTS = ['dense', 'hybrid', 'hybrid_rerank'] as const;
