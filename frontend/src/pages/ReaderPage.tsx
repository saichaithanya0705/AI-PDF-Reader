import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Headphones, Lightbulb, Loader2, MessageSquare, Wifi, WifiOff } from 'lucide-react';
import { usePDF } from '../context/usePDF';
import SmartPDFViewer from '../components/SmartPDFViewer';
import FloatingInsightsPanel from '../components/FloatingInsightsPanel';
import InsightsNotification from '../components/InsightsNotification';
import PodcastModal from '../components/PodcastModal';
import SimpleChatbot from '../components/SimpleChatbot';
import RelatedDocumentsSidebar from '../components/RelatedDocumentsSidebar';

const useMediaQuery = (query: string) => {
  const [matches, setMatches] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia(query).matches : false
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia(query);
    const handleChange = () => setMatches(mediaQuery.matches);

    handleChange();
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [query]);

  return matches;
};

const ReaderPage: React.FC = () => {
  const { pdfId } = useParams<{ pdfId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    documents,
    currentDocument,
    setCurrentDocument,
    loadDocument,
    getRelatedSections,
    getInsights,
    clearRelatedContent,
    insights,
    isOnline,
  } = usePDF();

  const parsedPage = Number.parseInt(searchParams.get('page') ?? '', 10);
  const currentPage = Number.isFinite(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  const [showFloatingInsights, setShowFloatingInsights] = useState(false);
  const [showPodcast, setShowPodcast] = useState(false);
  const [showInsightsNotification, setShowInsightsNotification] = useState(false);
  const [showChatbot, setShowChatbot] = useState(true);
  const [initialChatMessage, setInitialChatMessage] = useState<string>('');
  const [currentPersona, setCurrentPersona] = useState<string>('');
  const [currentJob, setCurrentJob] = useState<string>('');
  const [isDocumentLoading, setIsDocumentLoading] = useState(true);
  const [documentLoadError, setDocumentLoadError] = useState<string | null>(null);
  const isDockedChatViewport = useMediaQuery('(min-width: 1280px)');
  const readerRef = useRef<HTMLDivElement>(null);
  const isActiveDocument = Boolean(pdfId && currentDocument?.id === pdfId);

  useEffect(() => {
    clearRelatedContent();
    setShowInsightsNotification(false);
  }, [pdfId, clearRelatedContent]);

  useEffect(() => {
    if (!pdfId) {
      setIsDocumentLoading(false);
      setDocumentLoadError('Missing document ID.');
      return;
    }

    if (currentDocument?.id === pdfId) {
      setIsDocumentLoading(false);
      return;
    }

    let cancelled = false;
    setDocumentLoadError(null);

    const cachedDocument = documents.find((d) => d.id === pdfId);
    if (cachedDocument) {
      setCurrentDocument(cachedDocument);
      setIsDocumentLoading(false);
      return;
    }

    setIsDocumentLoading(true);
    loadDocument(pdfId).then((loadedDocument) => {
      if (cancelled) return;
      setIsDocumentLoading(false);
      if (!loadedDocument) {
        setDocumentLoadError('Document not found or you do not have access to it.');
      }
    });

    return () => {
      cancelled = true;
    };
  }, [pdfId, documents, currentDocument?.id, setCurrentDocument, loadDocument]);

  useEffect(() => {
    if (!pdfId || !isActiveDocument) return;
    getRelatedSections(pdfId, currentPage);
  }, [pdfId, isActiveDocument, currentPage, getRelatedSections]);

  useEffect(() => {
    if (!pdfId || !isActiveDocument || !isOnline) return;
    getInsights(pdfId, currentPage);
  }, [pdfId, isActiveDocument, currentPage, isOnline, getInsights]);

  useEffect(() => {
    const savedPersona = localStorage.getItem('lastPersona');
    const savedJob = localStorage.getItem('lastJob');
    if (savedPersona) setCurrentPersona(savedPersona);
    if (savedJob) setCurrentJob(savedJob);
  }, []);

  useEffect(() => {
    const insightsParam = searchParams.get('insights');
    const podcastParam = searchParams.get('podcast');

    if (insightsParam === 'true' && isOnline) {
      setShowFloatingInsights(true);
    }

    if (podcastParam === 'true' && isOnline) {
      const timer = setTimeout(() => {
        setShowPodcast(true);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [searchParams, isOnline]);

  useEffect(() => {
    if (insights && insights.length > 0 && !showFloatingInsights) {
      setShowInsightsNotification(true);
    }
  }, [insights, showFloatingInsights]);

  const handlePageChange = (page: number) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set('page', page.toString());
        return next;
      },
      { replace: true }
    );
  };

  if (isDocumentLoading || !currentDocument || !isActiveDocument) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-app-bg p-phi-5">
        <div className="w-full max-w-phi-modal-sm rounded-phi-lg border border-[rgba(25,24,22,0.1)] bg-app-surface p-phi-6 text-center shadow-card">
          {isDocumentLoading || !documentLoadError ? (
            <>
              <Loader2
                className="mx-auto mb-phi-3 h-5 w-5 animate-spin text-ink-muted"
                strokeWidth={1.5}
              />
              <p className="text-phi-sm font-medium text-ink-primary">Opening document</p>
              <p className="mt-phi-1 text-phi-xs text-ink-muted">
                Fetching the protected PDF from your library
              </p>
            </>
          ) : (
            <>
              <p className="text-phi-sm font-medium text-ink-primary">Unable to open document</p>
              <p className="mt-phi-2 text-phi-xs text-ink-secondary">{documentLoadError}</p>
            </>
          )}
          <button
            type="button"
            onClick={() => navigate('/library')}
            className="btn-secondary mt-phi-5 h-phi-ctrl-sm text-phi-xs"
          >
            Back to library
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-app-bg text-ink-primary" ref={readerRef}>
      {/* Reader Header */}
      <header className="z-30 shrink-0 border-b border-[rgba(25,24,22,0.09)] bg-app-surface">
        <div className="flex h-phi-bar items-center justify-between gap-phi-4 px-phi-4">
          <div className="flex min-w-0 items-center gap-phi-3">
            <button
              type="button"
              onClick={() => navigate('/library')}
              className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm shrink-0 items-center justify-center rounded-phi-md text-ink-secondary transition-colors duration-phi-fast hover:bg-app-raised hover:text-ink-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              aria-label="Back to library"
              title="Back to library"
            >
              <ArrowLeft className="h-4 w-4" strokeWidth={1.5} />
            </button>
            <div className="min-w-0">
              <h1 className="truncate text-phi-sm font-medium text-ink-primary" title={currentDocument.name}>
                {currentDocument.name}
              </h1>
              <p className="font-mono text-phi-2xs tabular-nums text-ink-muted">
                Page {currentPage}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-phi-2">
            {isOnline && (
              <>
                <button
                  type="button"
                  onClick={() => {
                    setShowFloatingInsights((prev) => !prev);
                    setShowInsightsNotification(false);
                  }}
                  className={`inline-flex h-phi-ctrl-sm items-center gap-phi-2 rounded-phi-md border px-phi-3 text-phi-xs font-medium transition-colors duration-phi-fast ${
                    showFloatingInsights
                      ? 'border-accent/40 bg-accent-soft text-accent-ink'
                      : 'border-[rgba(25,24,22,0.1)] bg-app-surface text-ink-secondary hover:bg-app-raised hover:text-ink-primary'
                  }`}
                >
                  <Lightbulb className="h-3.5 w-3.5" strokeWidth={1.5} />
                  <span className="hidden sm:inline">Insights</span>
                  {insights && insights.length > 0 && (
                    <span className="font-mono text-phi-2xs tabular-nums text-ink-muted">
                      {insights.length}
                    </span>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setShowPodcast(true)}
                  className="inline-flex h-phi-ctrl-sm items-center gap-phi-2 rounded-phi-md border border-[rgba(25,24,22,0.1)] bg-app-surface px-phi-3 text-phi-xs font-medium text-ink-secondary transition-colors duration-phi-fast hover:bg-app-raised hover:text-ink-primary"
                >
                  <Headphones className="h-3.5 w-3.5" strokeWidth={1.5} />
                  <span className="hidden sm:inline">Audio overview</span>
                </button>
              </>
            )}

            <button
              type="button"
              onClick={() => {
                setShowChatbot((prev) => !prev);
                if (showChatbot) {
                  setInitialChatMessage('');
                }
              }}
              className={`inline-flex h-phi-ctrl-sm items-center gap-phi-2 rounded-phi-md border px-phi-3 text-phi-xs font-medium transition-colors duration-phi-fast ${
                showChatbot
                  ? 'border-ink-primary bg-ink-primary text-paper-50'
                  : 'border-[rgba(25,24,22,0.1)] bg-app-surface text-ink-secondary hover:bg-app-raised hover:text-ink-primary'
              }`}
            >
              <MessageSquare className="h-3.5 w-3.5" strokeWidth={1.5} />
              <span>{showChatbot ? 'Hide chat' : 'Chat'}</span>
            </button>

            <span className="hidden h-phi-4 w-px bg-[rgba(25,24,22,0.1)] sm:inline-block" />

            <div
              className={`hidden items-center gap-phi-2 font-mono text-phi-2xs sm:flex ${
                isOnline ? 'text-semantic-positive' : 'text-semantic-warning'
              }`}
            >
              {isOnline ? (
                <Wifi className="h-3.5 w-3.5" strokeWidth={1.5} />
              ) : (
                <WifiOff className="h-3.5 w-3.5" strokeWidth={1.5} />
              )}
              <span>{isOnline ? 'Online' : 'Offline'}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Three-Pane Workspace */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <RelatedDocumentsSidebar currentDocumentId={currentDocument.id} />

        <div className="min-w-0 flex-1 overflow-hidden">
          <SmartPDFViewer
            key={currentDocument.id}
            document={currentDocument}
            initialPage={currentPage}
            onPageChange={handlePageChange}
            onTextSelection={() => {}}
            onAskLLM={(text, page) => {
              setInitialChatMessage(`Regarding the text on page ${page}: "${text}"\n\nQuestion: `);
              setShowChatbot(true);
            }}
          />
        </div>

        {showChatbot && isDockedChatViewport && (
          <aside className="h-full w-phi-chat shrink-0 overflow-hidden border-l border-[rgba(25,24,22,0.09)] bg-app-surface">
            <SimpleChatbot
              documentId={currentDocument?.id}
              documentContext={`Reading: ${currentDocument?.name} (Page ${currentPage})`}
              isMinimized={false}
              onToggleMinimize={() => {
                setShowChatbot(false);
                setInitialChatMessage('');
              }}
              initialMessage={initialChatMessage}
              viewType="pdf_viewer"
              currentPage={currentPage}
              variant="docked"
            />
          </aside>
        )}
      </div>

      {showChatbot && !isDockedChatViewport && (
        <SimpleChatbot
          documentId={currentDocument?.id}
          documentContext={`Reading: ${currentDocument?.name} (Page ${currentPage})`}
          isMinimized={false}
          onToggleMinimize={() => {
            setShowChatbot(false);
            setInitialChatMessage('');
          }}
          initialMessage={initialChatMessage}
          viewType="pdf_viewer"
          currentPage={currentPage}
        />
      )}

      <InsightsNotification
        isVisible={showInsightsNotification}
        onOpenInsights={() => {
          setShowFloatingInsights(true);
          setShowInsightsNotification(false);
        }}
        onDismiss={() => setShowInsightsNotification(false)}
        insightCount={insights?.length || 0}
      />

      <FloatingInsightsPanel
        isVisible={showFloatingInsights}
        onClose={() => setShowFloatingInsights(false)}
        currentPage={currentPage}
        position={{ x: 110, y: 78 }}
      />

      <PodcastModal
        isVisible={showPodcast}
        onClose={() => setShowPodcast(false)}
        documentId={currentDocument?.id || ''}
        currentPage={currentPage}
        persona={currentPersona}
        job={currentJob}
      />

      {!showChatbot && (
        <SimpleChatbot
          documentId={currentDocument?.id}
          documentContext={`Reading: ${currentDocument?.name} (Page ${currentPage})`}
          isMinimized
          onToggleMinimize={() => setShowChatbot(true)}
          initialMessage={initialChatMessage}
          viewType="pdf_viewer"
          currentPage={currentPage}
        />
      )}
    </div>
  );
};

export default ReaderPage;
