import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePDF } from '../context/usePDF';
import { ExternalLink, FileText, X } from 'lucide-react';

interface RelatedDocumentsSidebarProps {
  currentDocumentId?: string;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

const RelatedDocumentsSidebar: React.FC<RelatedDocumentsSidebarProps> = ({
  currentDocumentId,
  mobileOpen = false,
  onCloseMobile,
}) => {
  const { documents, crossDocumentSections, fetchAllDocuments } = usePDF();
  const navigate = useNavigate();

  useEffect(() => {
    if (documents.length === 0) {
      fetchAllDocuments();
    }
  }, [documents.length, fetchAllDocuments]);

  const handleNavigate = (docId: string, page: number = 1) => {
    onCloseMobile?.();
    navigate(`/reader/${docId}?page=${page}`);
  };

  if (documents.length <= 1 && crossDocumentSections.length === 0) {
    return null;
  }

  const sidebarContent = (
    <>
      <div className="border-b border-[rgba(25,24,22,0.08)] px-phi-4 py-phi-3">
        <div className="flex items-center justify-between gap-phi-2">
          <h3 className="text-phi-xs font-medium text-ink-primary">Workspace PDFs</h3>
          <div className="flex items-center gap-phi-2">
            <span className="font-mono text-phi-2xs tabular-nums text-ink-muted">
              {documents.length}
            </span>
            {onCloseMobile && (
              <button
                type="button"
                onClick={onCloseMobile}
                className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm text-ink-muted hover:bg-paper-200 hover:text-ink-primary xl:hidden"
                aria-label="Close workspace files"
              >
                <X className="h-4 w-4" strokeWidth={1.5} />
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto scrollbar-thin">
        <div className="space-y-phi-1 p-phi-3">
          {documents.map((document) => {
            const isActive = document.id === currentDocumentId;
            return (
              <button
                key={document.id}
                type="button"
                onClick={() => handleNavigate(document.id)}
                className={`w-full rounded-phi-md px-phi-3 py-phi-2 text-left transition-colors duration-phi-fast ${
                  isActive
                    ? 'folio-mark bg-app-surface text-ink-primary shadow-subtle ring-1 ring-[rgba(25,24,22,0.09)]'
                    : 'text-ink-secondary hover:bg-paper-200/70 hover:text-ink-primary'
                }`}
                title={document.name}
              >
                <div className="flex items-start gap-phi-3">
                  <FileText
                    className={`mt-phi-1 h-4 w-4 shrink-0 ${
                      isActive ? 'text-accent' : 'text-ink-muted'
                    }`}
                    strokeWidth={1.5}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-phi-xs font-medium">{document.name}</span>
                    <span className="mt-phi-1 block font-mono text-phi-2xs tabular-nums text-ink-muted">
                      {Math.max(1, Math.round((document.size || 0) / 1024))} KB
                    </span>
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        {crossDocumentSections.length === 0 && documents.length > 1 && (
          <p className="border-t border-[rgba(25,24,22,0.08)] p-phi-4 text-phi-xs leading-phi text-ink-muted">
            No closely related passages in your other PDFs for this page.
          </p>
        )}

        {crossDocumentSections.length > 0 && (
          <div className="border-t border-[rgba(25,24,22,0.08)] p-phi-3">
            <div className="mb-phi-3 px-phi-1">
              <h4 className="text-phi-xs font-medium text-ink-primary">Related passages</h4>
              <p className="mt-phi-1 text-phi-2xs text-ink-muted">
                Matches from other PDFs for this page
              </p>
            </div>

            <div className="space-y-phi-2">
              {crossDocumentSections.map((section) => (
                <button
                  key={`${section.documentId}-${section.page}-${section.id}`}
                  type="button"
                  className="group w-full rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-app-surface p-phi-3 text-left transition-colors duration-phi-fast hover:border-[rgba(25,24,22,0.22)]"
                  onClick={() => handleNavigate(section.documentId, section.page)}
                >
                  <div className="flex items-start justify-between gap-phi-2">
                    <span
                      className="min-w-0 flex-1 truncate text-phi-xs font-medium text-ink-primary group-hover:text-accent-ink"
                      title={section.documentName}
                    >
                      {section.documentName}
                    </span>
                    <ExternalLink
                      className="mt-phi-1 h-3.5 w-3.5 shrink-0 text-ink-faint opacity-0 transition-opacity duration-phi-fast group-hover:opacity-100"
                      strokeWidth={1.5}
                    />
                  </div>

                  <div className="mt-phi-1 flex items-center gap-phi-2 font-mono text-phi-2xs tabular-nums text-ink-muted">
                    <span className="text-accent-ink">p. {section.page}</span>
                    <span>·</span>
                    <span title="Retrieval score (0.8 × semantic similarity + 0.2 × keyword match). Higher is more related.">
                      score {section.relevance.toFixed(2)}
                    </span>
                  </div>

                  <p className="mt-phi-2 line-clamp-3 border-l-2 border-[rgba(25,24,22,0.12)] pl-phi-3 text-phi-xs leading-phi text-ink-secondary transition-colors duration-phi-fast group-hover:border-accent">
                    {section.snippet}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  );

  return (
    <>
      <aside className="hidden h-full w-phi-sidebar shrink-0 flex-col overflow-hidden border-r border-[rgba(25,24,22,0.09)] bg-paper-50 xl:flex">
        {sidebarContent}
      </aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 flex xl:hidden" role="dialog" aria-modal="true" aria-label="Workspace PDFs">
          <button
            type="button"
            aria-label="Close workspace sidebar backdrop"
            className="flex-1 bg-ink-primary/35 backdrop-blur-[1px]"
            onClick={onCloseMobile}
          />
          <aside className="order-first flex h-full w-phi-sidebar max-w-[85vw] flex-col overflow-hidden border-r border-[rgba(25,24,22,0.12)] bg-paper-50 shadow-float">
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
};

export default RelatedDocumentsSidebar;
