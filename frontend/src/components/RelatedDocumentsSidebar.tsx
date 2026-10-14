import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePDF } from '../context/usePDF';
import { ExternalLink, FileText } from 'lucide-react';

interface RelatedDocumentsSidebarProps {
  currentDocumentId?: string;
}

const RelatedDocumentsSidebar: React.FC<RelatedDocumentsSidebarProps> = ({ currentDocumentId }) => {
  const { documents, crossDocumentSections, fetchAllDocuments } = usePDF();
  const navigate = useNavigate();

  // The reader can be opened directly (deep link / refresh) without visiting the
  // library first, so load the full document list here rather than relying on
  // whatever happens to be cached.
  useEffect(() => {
    fetchAllDocuments();
  }, [fetchAllDocuments]);

  const handleNavigate = (docId: string, page: number = 1) => {
    navigate(`/reader/${docId}?page=${page}`);
  };

  if (documents.length <= 1 && crossDocumentSections.length === 0) {
    return null;
  }

  return (
    <aside className="hidden h-full w-72 shrink-0 flex-col overflow-hidden border-r border-slate-700 bg-slate-900/95 lg:flex">
      <div className="border-b border-slate-700 p-4">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-white">
          <FileText className="h-4 w-4 text-cyan-300" />
          Uploaded PDFs
        </h3>
        <p className="mt-1 text-xs text-slate-400">
          {documents.length} file{documents.length === 1 ? '' : 's'} available in this workspace
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="space-y-2 p-3">
          {documents.map((document) => {
            const isActive = document.id === currentDocumentId;
            return (
              <button
                key={document.id}
                onClick={() => handleNavigate(document.id)}
                className={`w-full rounded-lg border p-3 text-left transition-colors ${
                  isActive
                    ? 'border-cyan-400/50 bg-cyan-400/10 text-white'
                    : 'border-slate-700 bg-slate-800/70 text-slate-200 hover:border-slate-500 hover:bg-slate-800'
                }`}
                title={document.name}
              >
                <div className="flex items-start gap-3">
                  <span className={`mt-0.5 rounded-md p-1.5 ${isActive ? 'bg-cyan-400/20 text-cyan-200' : 'bg-slate-700 text-slate-300'}`}>
                    <FileText className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{document.name}</span>
                    <span className="mt-1 block text-xs text-slate-400">
                      {Math.max(1, Math.round((document.size || 0) / 1024))} KB
                    </span>
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        {crossDocumentSections.length === 0 && documents.length > 1 && (
          <p className="border-t border-slate-700 p-3 text-xs text-slate-500">
            No closely related passages in your other PDFs for this page.
          </p>
        )}

        {crossDocumentSections.length > 0 && (
          <div className="border-t border-slate-700 p-3">
            <div className="mb-3">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
                Relevant Lines
              </h4>
              <p className="mt-1 text-xs text-slate-500">
                Matches from other PDFs for the current page
              </p>
            </div>

            <div className="space-y-2">
              {crossDocumentSections.map((section) => (
                <button
                  key={`${section.documentId}-${section.page}-${section.id}`}
                  className="group w-full rounded-lg border border-slate-700 bg-slate-800/60 p-3 text-left transition-colors hover:border-indigo-400/50 hover:bg-slate-800"
                  onClick={() => handleNavigate(section.documentId, section.page)}
                >
                  <div className="mb-2 flex items-start gap-2">
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-cyan-200" title={section.documentName}>
                        {section.documentName}
                      </span>
                      <span className="mt-1 inline-flex items-center gap-2 text-xs text-slate-400">
                        Page {section.page}
                        <span
                          className="rounded bg-indigo-400/10 px-1.5 py-0.5 tabular-nums text-indigo-200"
                          title="Retrieval score (0.8 × semantic similarity + 0.2 × keyword match). Higher is more related; it is not a percentage."
                        >
                          score {section.relevance.toFixed(2)}
                        </span>
                      </span>
                    </span>
                    <ExternalLink className="h-3.5 w-3.5 shrink-0 text-slate-500 opacity-0 transition-opacity group-hover:opacity-100" />
                  </div>
                  <p className="line-clamp-3 border-l-2 border-slate-700 pl-2 text-xs leading-relaxed text-slate-300 group-hover:border-indigo-400/50">
                    {section.snippet}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};

export default RelatedDocumentsSidebar;
