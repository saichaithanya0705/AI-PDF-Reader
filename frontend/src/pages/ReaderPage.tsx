import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, MessageSquare, Wifi, WifiOff } from 'lucide-react';
import { usePDF } from '../context/usePDF';
import SmartPDFViewer from '../components/SmartPDFViewer';
import FloatingInsightsPanel from '../components/FloatingInsightsPanel';
import InsightsNotification from '../components/InsightsNotification';
import PodcastModal from '../components/PodcastModal';
import SimpleChatbot from '../components/SimpleChatbot';
import RelatedDocumentsSidebar from '../components/RelatedDocumentsSidebar';

const useMediaQuery = (query: string) => {
  const [matches, setMatches] = useState(() => (
    typeof window !== 'undefined' ? window.matchMedia(query).matches : false
  ));

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
    insights,
    isOnline,
  } = usePDF();

  // Initialize page from URL or default to 1
  const pageParam = searchParams.get('page');
  const initialPage = pageParam ? parseInt(pageParam, 10) : 1;
  const [currentPage, setCurrentPage] = useState(initialPage);

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

  useEffect(() => {
    if (!pdfId) {
      setIsDocumentLoading(false);
      setDocumentLoadError('Missing document ID.');
      return;
    }

    let cancelled = false;

    const resolveDocument = async () => {
      setDocumentLoadError(null);

      const doc = currentDocument?.id === pdfId
        ? currentDocument
        : documents.find(d => d.id === pdfId);

      if (doc) {
        setCurrentDocument(doc);
        setIsDocumentLoading(false);
        getRelatedSections(pdfId, currentPage);
        if (isOnline) {
          getInsights(pdfId, currentPage);
        }
        return;
      }

      setIsDocumentLoading(true);
      const loadedDocument = await loadDocument(pdfId);
      if (cancelled) return;

      if (loadedDocument) {
        setIsDocumentLoading(false);
        getRelatedSections(pdfId, currentPage);
        if (isOnline) {
          getInsights(pdfId, currentPage);
        }
      } else {
        setIsDocumentLoading(false);
        setDocumentLoadError('Document not found or you do not have access to it.');
      }
    };

    resolveDocument();

    return () => {
      cancelled = true;
    };
  }, [
    pdfId,
    documents,
    currentDocument,
    currentPage,
    isOnline,
    setCurrentDocument,
    loadDocument,
    getRelatedSections,
    getInsights,
  ]);

  // Load saved persona and job only once on mount
  useEffect(() => {
    const savedPersona = localStorage.getItem('lastPersona');
    const savedJob = localStorage.getItem('lastJob');
    if (savedPersona) setCurrentPersona(savedPersona);
    if (savedJob) setCurrentJob(savedJob);
  }, []); // Only run once on mount

  // Handle URL parameters for auto-opening features
  useEffect(() => {
    const insights = searchParams.get('insights');
    const podcast = searchParams.get('podcast');

    if (insights === 'true' && isOnline) {
      setShowFloatingInsights(true);
    }

    if (podcast === 'true' && isOnline) {
      // Small delay to ensure document is loaded
      setTimeout(() => {
        setShowPodcast(true);
      }, 1000);
    }
  }, [searchParams, isOnline]);

  // Show notification when insights are available
  useEffect(() => {
    if (insights && insights.length > 0 && !showFloatingInsights) {
      setShowInsightsNotification(true);
    }
  }, [insights, showFloatingInsights]);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);

    // Update URL without reloading
    setSearchParams(prev => {
      prev.set('page', page.toString());
      return prev;
    }, { replace: true });

    if (currentDocument) {
      getRelatedSections(currentDocument.id, page);
      if (isOnline) {
        getInsights(currentDocument.id, page);
      }
    }
  };

  if (isDocumentLoading || !currentDocument) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="text-center p-8 bg-slate-800 rounded-lg border border-slate-700">
          {isDocumentLoading ? (
            <>
              <div className="animate-spin w-12 h-12 border-4 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4"></div>
              <p className="text-white text-lg mb-2">Loading document...</p>
              <p className="text-slate-400 text-sm">Fetching the protected document from your library.</p>
            </>
          ) : (
            <>
              <p className="text-white text-lg mb-2">Unable to open document</p>
              <p className="text-slate-400 text-sm">{documentLoadError}</p>
            </>
          )}
          <button
            onClick={() => navigate('/library')}
            className="mt-4 px-4 py-2 bg-cyan-600 text-white rounded hover:bg-cyan-700 transition-colors"
          >
            Back to library
          </button>
        </div>
      </div>
    );
  }

  // Debug: Log when reader renders (removed to prevent re-render loops)
  // console.log('🎯 Reader rendering with document:', currentDocument?.name, 'ID:', currentDocument?.id);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950" ref={readerRef}>
      {/* Header */}
      <header className="bg-slate-900/90 backdrop-blur border-b border-slate-700 sticky top-0 z-40">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/library')}
              className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </button>
            <div>
              <h1 className="text-xl font-semibold text-white truncate max-w-md">
                {currentDocument.name}
              </h1>
              <p className="text-sm text-slate-400">Page {currentPage}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setShowChatbot(prev => !prev);
                if (showChatbot) {
                  setInitialChatMessage('');
                }
              }}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                showChatbot
                  ? 'bg-blue-500/20 text-blue-100 hover:bg-blue-500/30'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white'
              }`}
            >
              <MessageSquare className="h-4 w-4" />
              {showChatbot ? 'Hide chat' : 'Chat'}
            </button>

            {/* Online/Offline Indicator */}
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium ${isOnline
              ? 'bg-green-400/10 text-green-400 border border-green-400/20'
              : 'bg-orange-400/10 text-orange-400 border border-orange-400/20'
              }`}>
              {isOnline ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
              {isOnline ? 'Online' : 'Offline'}
            </div>


          </div>
        </div>
      </header>

      {/* Main Content - Integrated PDF Viewer with Built-in Recommendations */}
      <div className="flex flex-1 h-[calc(100vh-80px)] overflow-hidden">
        <RelatedDocumentsSidebar currentDocumentId={currentDocument.id} />

        <div className="min-w-0 flex-1 p-4 overflow-hidden h-full">
          <SmartPDFViewer
            document={currentDocument}
            initialPage={initialPage}
            onPageChange={handlePageChange}
            onTextSelection={(text, page) => {
              console.log(`📝 Text selected on page ${page}:`, text.substring(0, 100) + '...');
            }}
            onAskLLM={(text, page) => {
              console.log(`🤖 Ask LLM clicked on page ${page} with text:`, text.substring(0, 100) + '...');
              // Open chatbot and pre-fill with selected text
              setInitialChatMessage(`Regarding the text on page ${page}: "${text}"\n\nQuestion: `);
              setShowChatbot(true);
            }}
          />
        </div>

        {showChatbot && isDockedChatViewport && (
          <aside className="h-full w-[400px] min-w-[360px] max-w-[420px] shrink-0 overflow-hidden border-l border-slate-700 bg-slate-900">
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



      {/* Insights Notification */}
      <InsightsNotification
        isVisible={showInsightsNotification}
        onOpenInsights={() => {
          setShowFloatingInsights(true);
          setShowInsightsNotification(false);
        }}
        onDismiss={() => setShowInsightsNotification(false)}
        insightCount={insights?.length || 0}
      />

      {/* Floating Insights Panel */}
      <FloatingInsightsPanel
        isVisible={showFloatingInsights}
        onClose={() => setShowFloatingInsights(false)}
        position={{ x: 100, y: 100 }}
      />

      {/* Podcast Modal */}
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
    </div >
  );
};

export default ReaderPage;
