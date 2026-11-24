export interface ChatCitation {
  id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  text: string;
  similarity: number;
}

const isRecord = (value: unknown): value is Record<string, unknown> => (
  typeof value === 'object' && value !== null
);

const normalizeCitationList = (value: unknown): ChatCitation[] => {
  if (!Array.isArray(value)) return [];

  return value
    .filter(isRecord)
    .map((entry) => {
      const pageNumber =
        typeof entry.page_number === 'number'
          ? entry.page_number
          : typeof entry.page === 'number'
            ? entry.page
            : 1;
      const documentId = typeof entry.document_id === 'string' ? entry.document_id : '';
      return {
        id: typeof entry.id === 'string' ? entry.id : `${documentId || 'doc'}-${pageNumber}`,
        document_id: documentId,
        document_name: typeof entry.document_name === 'string' ? entry.document_name : 'Document',
        page_number: pageNumber,
        text: typeof entry.text === 'string' ? entry.text : '',
        similarity: typeof entry.similarity === 'number' ? entry.similarity : 0,
      };
    })
    .filter((entry) => entry.document_id.length > 0);
};

/**
 * Extract grounded citations from chat payloads without letting empty arrays mask sources.
 */
export const extractChatCitations = (
  payload: Record<string, unknown>,
  context: Record<string, unknown> = {}
): ChatCitation[] => {
  const candidates = [
    ...normalizeCitationList(payload.sources),
    ...normalizeCitationList(payload.related_documents),
    ...normalizeCitationList(context.search_results),
    ...normalizeCitationList(context.related_documents),
  ];

  const seen = new Set<string>();
  const deduplicated: ChatCitation[] = [];
  for (const item of candidates) {
    const key = `${item.document_id}:${item.page_number}`;
    if (seen.has(key)) continue;
    seen.add(key);
    deduplicated.push(item);
  }

  return deduplicated;
};
