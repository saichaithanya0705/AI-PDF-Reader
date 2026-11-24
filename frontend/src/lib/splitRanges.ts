export interface SplitPageRange {
  name: string;
  startPage: number;
  endPage: number;
}

/**
 * Distribute a multi-page PDF evenly across `requestedSplits` non-overlapping parts.
 */
export const buildSplitRanges = (
  totalPages: number,
  requestedSplits: number,
  existingNames: readonly string[] = []
): SplitPageRange[] => {
  const safeTotal = Math.max(2, Math.floor(totalPages));
  const maxSplits = Math.min(10, safeTotal);
  const clamped = Math.min(maxSplits, Math.max(2, Math.floor(requestedSplits) || 2));
  const basePages = Math.floor(safeTotal / clamped);
  const remainder = safeTotal % clamped;

  const ranges: SplitPageRange[] = [];
  let cursor = 1;
  for (let i = 0; i < clamped; i += 1) {
    const count = basePages + (i < remainder ? 1 : 0);
    const startPage = cursor;
    const endPage = cursor + count - 1;
    cursor = endPage + 1;
    ranges.push({
      name: existingNames[i] || '',
      startPage,
      endPage,
    });
  }

  return ranges;
};
