import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowUpDown,
  Headphones,
  Lightbulb,
  Loader2,
  MessageSquare,
  PanelLeft,
  RefreshCw,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react';
import { usePDF } from '../context/usePDF';
import SmartPDFViewer from '../components/SmartPDFViewer';
import FloatingInsightsPanel from '../components/FloatingInsightsPanel';
import PodcastModal from '../components/PodcastModal';
import SimpleChatbot from '../components/SimpleChatbot';
import RelatedDocumentsSidebar from '../components/RelatedDocumentsSidebar';
import {
  getReaderSidebarLayout,
  type SidebarSplitFocus,
  type StudioToolTab,
} from '../lib/readerSidebarLayout';

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
    isLoadingInsights,
    isOnline,
  } = usePDF();

  const parsedPage = Number.parseInt(searchParams.get('page') ?? '', 10);
  const currentPage = Number.isFinite(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  const isDockedChatViewport = useMediaQuery('(min-width: 1280px)');
  const [activeStudioTab, setActiveStudioTab] = useState<StudioToolTab | null>('insights');
  const [showChatbot, setShowChatbot] = useState(true);
  const [sidebarSplitFocus, setSidebarSplitFocus] = useState<SidebarSplitFocus>('chat-primary');
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);
  const [initialChatMessage, setInitialChatMessage] = useState<string>('');
  const [currentPersona, setCurrentPersona] = useState<string>('');
  const [currentJob, setCurrentJob] = useState<string>('');
  const [isDocumentLoading, setIsDocumentLoading] = useState(true);
  const [documentLoadError, setDocumentLoadError] = useState<string | null>(null);
  const readerRef = useRef<HTMLDivElement>(null);
  const isActiveDocument = Boolean(pdfId && currentDocument?.id === pdfId);

  useEffect(() => {
    clearRelatedContent();
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
    if (activeStudioTab !== 'insights' || !pdfId || !isActiveDocument || !isOnline) return;
    getInsights(pdfId, currentPage);
  }, [activeStudioTab, pdfId, isActiveDocument, currentPage, isOnline, getInsights]);

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
      setActiveStudioTab('insights');
    } else if (podcastParam === 'true' && isOnline) {
      setActiveStudioTab('audio');
    }
  }, [searchParams, isOnline]);

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

  const sidebarLayout = getReaderSidebarLayout(
    activeStudioTab !== null,
    showChatbot,
    sidebarSplitFocus
  );
  const splitLabel = sidebarSplitFocus === 'chat-primary' ? 'φ · 38 / 62' : 'φ · 62 / 38';

  const studioSection = activeStudioTab !== null && (
    <section aria-label="Page studio tools" className="flex min-h-0 flex-col overflow-hidden">
      <div className="flex h-phi-ctrl shrink-0 items-center justify-between gap-phi-2 border-b border-[rgba(25,24,22,0.08)] bg-paper-50 px-phi-3">
        <div
          className="flex items-center gap-phi-1 rounded-phi-sm bg-paper-200/70 p-0.5"
          role="tablist"
          aria-label="Studio tools"
        >
          <button
            type="button"
            role="tab"
            aria-selected={activeStudioTab === 'insights'}
            onClick={() => setActiveStudioTab('insights')}
            className={`inline-flex items-center gap-phi-1 rounded-phi-xs px-phi-2 py-1 text-phi-xs font-medium transition-colors duration-phi-fast ${
              activeStudioTab === 'insights'
                ? 'bg-app-surface text-ink-primary shadow-subtle'
                : 'text-ink-secondary hover:text-ink-primary'
            }`}
          >
            <Lightbulb className="h-3.5 w-3.5 text-accent" strokeWidth={1.5} />
            <span>Insights</span>
            {insights.length > 0 && (
              <span className="font-mono text-phi-2xs tabular-nums text-ink-muted">
                {insights.length}
              </span>
            )}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeStudioTab === 'audio'}
            onClick={() => setActiveStudioTab('audio')}
            className={`inline-flex items-center gap-phi-1 rounded-phi-xs px-phi-2 py-1 text-phi-xs font-medium transition-colors duration-phi-fast ${
              activeStudioTab === 'audio'
                ? 'bg-app-surface text-ink-primary shadow-subtle'
                : 'text-ink-secondary hover:text-ink-primary'
            }`}
          >
            <Headphones className="h-3.5 w-3.5 text-accent" strokeWidth={1.5} />
            <span>Audio</span>
          </button>
        </div>

        <div className="flex items-center gap-phi-1">
          <span className="font-mono text-phi-2xs tabular-nums text-ink-muted">
            p. {currentPage}
          </span>
          {activeStudioTab === 'insights' && isOnline && (
            <button
              type="button"
              onClick={() => getInsights(currentDocument.id, currentPage, true)}
              disabled={isLoadingInsights}
              className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary disabled:opacity-40"
              title="Refresh insights"
              aria-label="Refresh insights"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${isLoadingInsights ? 'animate-spin' : ''}`}
                strokeWidth={1.5}
              />
            </button>
          )}
          <button
            type="button"
            onClick={() => setActiveStudioTab(null)}
            className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
            title="Close studio panel"
            aria-label="Close studio panel"
          >
            <X className="h-4 w-4" strokeWidth={1.5} />
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        {activeStudioTab === 'insights' ? (
          <FloatingInsightsPanel
            isVisible
            onClose={() => setActiveStudioTab(null)}
            currentPage={currentPage}
            variant="docked"
            hideHeader
          />
        ) : (
          <PodcastModal
            isVisible
            onClose={() => setActiveStudioTab(null)}
            documentId={currentDocument.id}
            currentPage={currentPage}
            persona={currentPersona}
            job={currentJob}
            variant="docked"
            hideHeader
          />
        )}
      </div>
    </section>
  );

  const phiDivider = sidebarLayout.isSplit && (
    <div
      role="separator"
      aria-orientation="horizontal"
      aria-label="Golden ratio sidebar divider"
      className="flex h-6 shrink-0 items-center justify-between border-y border-[rgba(25,24,22,0.09)] bg-paper-100/80 px-phi-3"
    >
      <span className="font-mono text-phi-2xs tabular-nums text-ink-muted">{splitLabel}</span>
      <button
        type="button"
        onClick={() =>
          setSidebarSplitFocus((prev) =>
            prev === 'chat-primary' ? 'studio-primary' : 'chat-primary'
          )
        }
        className="inline-flex items-center gap-phi-1 rounded-phi-xs px-phi-2 py-0.5 text-phi-2xs font-medium text-ink-secondary transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
        title="Swap golden ratio split"
        aria-label="Swap golden ratio split"
      >
        <ArrowUpDown className="h-3 w-3" strokeWidth={1.5} />
        <span>Swap ratio</span>
      </button>
    </div>
  );

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
            <button
              type="button"
              onClick={() => setShowMobileSidebar((prev) => !prev)}
              className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm shrink-0 items-center justify-center rounded-phi-md border border-[rgba(25,24,22,0.1)] text-ink-secondary transition-colors duration-phi-fast hover:bg-app-raised hover:text-ink-primary xl:hidden"
              aria-label="Workspace PDFs and related passages"
              title="Workspace PDFs and related passages"
            >
              <PanelLeft className="h-4 w-4" strokeWidth={1.5} />
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
                  onClick={() =>
                    setActiveStudioTab((prev) => (prev === 'insights' ? null : 'insights'))
                  }
                  className={`inline-flex h-phi-ctrl-sm items-center gap-phi-2 rounded-phi-md border px-phi-3 text-phi-xs font-medium transition-colors duration-phi-fast ${
                    activeStudioTab === 'insights'
                      ? 'border-accent/40 bg-accent-soft text-accent-ink'
                      : 'border-[rgba(25,24,22,0.1)] bg-app-surface text-ink-secondary hover:bg-app-raised hover:text-ink-primary'
                  }`}
                >
                  <Lightbulb className="h-3.5 w-3.5" strokeWidth={1.5} />
                  <span className="hidden sm:inline">Insights</span>
                  {insights.length > 0 && (
                    <span className="font-mono text-phi-2xs tabular-nums text-ink-muted">
                      {insights.length}
                    </span>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setActiveStudioTab((prev) => (prev === 'audio' ? null : 'audio'))
                  }
                  className={`inline-flex h-phi-ctrl-sm items-center gap-phi-2 rounded-phi-md border px-phi-3 text-phi-xs font-medium transition-colors duration-phi-fast ${
                    activeStudioTab === 'audio'
                      ? 'border-accent/40 bg-accent-soft text-accent-ink'
                      : 'border-[rgba(25,24,22,0.1)] bg-app-surface text-ink-secondary hover:bg-app-raised hover:text-ink-primary'
                  }`}
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
        <RelatedDocumentsSidebar
          currentDocumentId={currentDocument.id}
          mobileOpen={showMobileSidebar}
          onCloseMobile={() => setShowMobileSidebar(false)}
        />

        <div className="min-w-0 flex-[1.618] overflow-hidden">
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

        {sidebarLayout.isOpen && (
          <aside
            aria-label="Reader studio sidebar"
            className="grid h-full w-[38.2%] min-w-[18.5rem] max-w-[26rem] flex-[1] shrink-0 overflow-hidden border-l border-[rgba(25,24,22,0.09)] bg-app-surface"
            style={{ gridTemplateRows: sidebarLayout.gridTemplateRows }}
          >
            {studioSection}
            {phiDivider}
            {showChatbot && isDockedChatViewport && (
              <section aria-label="Document assistant" className="flex min-h-0 flex-col overflow-hidden">
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
              </section>
            )}
            {showChatbot && !isDockedChatViewport && (
              <section aria-label="Document assistant" className="flex min-h-0 flex-col overflow-hidden">
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
              </section>
            )}
          </aside>
        )}
      </div>
    </div>
  );
};

export default ReaderPage;
