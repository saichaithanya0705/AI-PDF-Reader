import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import type { PDFPageProxy } from 'pdfjs-dist/types/src/display/api';
import { PDFDocument } from '../context/PDFContext';
import { API_URL } from '../config';
import { fetchAuthenticatedBlobUrl, fetchAuthenticatedBytes, generateAudio } from '../lib/api';
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Loader2,
  MessageSquare,
  Copy,
  Volume2,
  Check,
} from 'lucide-react';
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

const pdfWorkerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

pdfjs.GlobalWorkerOptions.workerSrc = `${pdfWorkerSrc}?v=20260612-mjs`;

interface SimplePDFViewerProps {
  document: PDFDocument;
  onPageChange: (page: number) => void;
  onTextSelection?: (text: string, page: number) => void;
  onAskLLM?: (text: string, page: number) => void;
  initialPage?: number;
}

interface SelectionMenuPosition {
  x: number;
  y: number;
}

const SimplePDFViewer: React.FC<SimplePDFViewerProps> = ({
  document: pdfDocument,
  onPageChange,
  onTextSelection,
  onAskLLM,
  initialPage = 1,
}) => {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(initialPage);
  const [scale, setScale] = useState<number>(1.0);
  const [deskWidth, setDeskWidth] = useState<number>(0);
  const [selectedText, setSelectedText] = useState<string>('');
  const [menuPosition, setMenuPosition] = useState<SelectionMenuPosition | null>(null);
  const [copied, setCopied] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [pageVoiceGenerating, setPageVoiceGenerating] = useState(false);
  const [currentPageText, setCurrentPageText] = useState<string>('');
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);
  const [voiceoverError, setVoiceoverError] = useState<string | null>(null);
  const [authenticatedPdfData, setAuthenticatedPdfData] = useState<Uint8Array | null>(null);
  const [pdfLoadError, setPdfLoadError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const deskRef = useRef<HTMLDivElement>(null);
  const audioObjectUrlRef = useRef<string | null>(null);
  const fittedPageWidth = deskWidth > 0 ? Math.max(220, Math.min(deskWidth, 880)) : undefined;
  const pdfUrl = pdfDocument.url?.startsWith('http') ? pdfDocument.url : `${API_URL}${pdfDocument.url}`;
  const pdfFile = useMemo(
    () => (authenticatedPdfData ? { data: authenticatedPdfData.slice() } : null),
    [authenticatedPdfData]
  );

  useEffect(() => () => {
    currentAudio?.pause();
  }, [currentAudio]);

  useEffect(() => () => {
    if (audioObjectUrlRef.current) {
      URL.revokeObjectURL(audioObjectUrlRef.current);
      audioObjectUrlRef.current = null;
    }
  }, []);

  useEffect(() => {
    const deskElement = deskRef.current;
    if (!deskElement || typeof ResizeObserver === 'undefined') return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      setDeskWidth(Math.max(0, Math.floor(entry.contentRect.width - 32)));
    });

    observer.observe(deskElement);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;
    setAuthenticatedPdfData(null);
    setPdfLoadError(null);

    fetchAuthenticatedBytes(pdfUrl)
      .then((pdfData) => {
        if (!cancelled) {
          setAuthenticatedPdfData(pdfData);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          console.error('Failed to load protected PDF file:', error);
          setPdfLoadError('Unable to load the protected PDF file.');
        }
      });

    return () => {
      cancelled = true;
    };
  }, [pdfUrl]);

  const handlePageLoadSuccess = useCallback(async (page: PDFPageProxy) => {
    try {
      const textContent = await page.getTextContent();
      const combinedText = (textContent.items as Array<{ str?: unknown }>)
        .map((item) => (typeof item.str === 'string' ? item.str : ''))
        .join(' ')
        .replace(/\s+/g, ' ')
        .trim();
      setCurrentPageText(combinedText);
    } catch (error) {
      console.error('Failed to extract text for voiceover:', error);
      setCurrentPageText('');
    }
  }, []);

  const requestVoiceover = useCallback(
    async (text: string) => {
      setVoiceoverError(null);
      const data = await generateAudio(text, pdfDocument.id, pageNumber);
      const audioPath =
        data && typeof data === 'object'
          ? (data as { audioUrl?: unknown; audio_url?: unknown }).audioUrl ??
            (data as { audio_url?: unknown }).audio_url
          : undefined;

      if (typeof audioPath === 'string' && audioPath.trim()) {
        currentAudio?.pause();
        if (audioObjectUrlRef.current) {
          URL.revokeObjectURL(audioObjectUrlRef.current);
          audioObjectUrlRef.current = null;
        }

        const audioObjectUrl = await fetchAuthenticatedBlobUrl(audioPath);
        audioObjectUrlRef.current = audioObjectUrl;
        const audio = new Audio(audioObjectUrl);
        setCurrentAudio(audio);
        await audio.play();
      }
    },
    [currentAudio, pageNumber, pdfDocument.id]
  );

  useEffect(() => {
    setPageNumber(initialPage);
  }, [initialPage]);

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setPdfLoadError(null);
    setNumPages(numPages);
    setPageNumber((page) => Math.min(Math.max(page, 1), numPages));
  }, []);

  const onDocumentLoadError = useCallback((error: Error) => {
    console.error('React-PDF failed to render authenticated PDF data:', error);
    setPdfLoadError(error.message || 'Unable to render the protected PDF file.');
  }, []);

  useEffect(() => {
    const handleSelection = () => {
      const selection = window.getSelection();
      const text = selection?.toString().trim();

      if (!selection || !text || text.length < 2 || selection.rangeCount === 0) {
        setSelectedText('');
        setMenuPosition(null);
        setCopied(false);
        return;
      }

      const range = selection.getRangeAt(0);
      const selectionNode = range.commonAncestorContainer;
      const selectionElement =
        selectionNode.nodeType === Node.ELEMENT_NODE
          ? (selectionNode as Element)
          : selectionNode.parentElement;
      const textLayer = selectionElement?.closest('.react-pdf__Page__textContent');
      const isPdfTextSelection = Boolean(
        textLayer && containerRef.current?.contains(textLayer)
      );

      if (isPdfTextSelection) {
        setSelectedText(text);
        const rect = range?.getBoundingClientRect();
        if (rect) {
          setMenuPosition({
            x: rect.left + rect.width / 2,
            y: rect.top - 10,
          });
        }
      } else {
        setSelectedText('');
        setMenuPosition(null);
        setCopied(false);
      }
    };

    window.document.addEventListener('mouseup', handleSelection);
    window.document.addEventListener('selectionchange', handleSelection);

    return () => {
      window.document.removeEventListener('mouseup', handleSelection);
      window.document.removeEventListener('selectionchange', handleSelection);
    };
  }, []);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(selectedText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleAskLLM = () => {
    if (!selectedText.trim()) return;

    if (onAskLLM) {
      onAskLLM(selectedText, pageNumber);
    }
    if (onTextSelection) {
      onTextSelection(selectedText, pageNumber);
    }
    window.getSelection()?.removeAllRanges();
    setSelectedText('');
    setMenuPosition(null);
  };

  const handleGenerateVoice = async () => {
    if (!selectedText || generating) return;

    setGenerating(true);
    try {
      await requestVoiceover(selectedText);
    } catch (err) {
      console.error('Failed to generate voice:', err);
      setVoiceoverError(err instanceof Error ? err.message : 'Unable to generate voiceover right now.');
    } finally {
      setGenerating(false);
    }
  };

  const handlePageVoiceover = async () => {
    if (!currentPageText || pageVoiceGenerating) return;

    setPageVoiceGenerating(true);
    try {
      await requestVoiceover(currentPageText);
    } catch (err) {
      console.error('Failed to generate page voiceover:', err);
      setVoiceoverError(err instanceof Error ? err.message : 'Unable to generate page voiceover right now.');
    } finally {
      setPageVoiceGenerating(false);
    }
  };

  const goToPrevPage = () => {
    if (pageNumber > 1) {
      setPageNumber(pageNumber - 1);
      onPageChange(pageNumber - 1);
    }
  };

  const goToNextPage = () => {
    if (pageNumber < numPages) {
      setPageNumber(pageNumber + 1);
      onPageChange(pageNumber + 1);
    }
  };

  return (
    <div className="flex h-full flex-col bg-app-canvas text-ink-primary" ref={containerRef}>
      {/* Viewer Controls Toolbar */}
      <div className="flex h-phi-ctrl shrink-0 items-center justify-between border-b border-[rgba(25,24,22,0.08)] bg-paper-50 px-phi-4">
        <div className="flex items-center gap-phi-2">
          <button
            type="button"
            onClick={goToPrevPage}
            disabled={pageNumber <= 1}
            className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm border border-[rgba(25,24,22,0.1)] bg-app-surface text-ink-secondary transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary disabled:opacity-40"
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" strokeWidth={1.5} />
          </button>
          <span className="min-w-[4.5rem] text-center font-mono text-phi-xs tabular-nums text-ink-secondary">
            {pageNumber} / {numPages || '—'}
          </span>
          <button
            type="button"
            onClick={goToNextPage}
            disabled={pageNumber >= numPages}
            className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm border border-[rgba(25,24,22,0.1)] bg-app-surface text-ink-secondary transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary disabled:opacity-40"
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" strokeWidth={1.5} />
          </button>
        </div>

        <div className="flex items-center gap-phi-2">
          <button
            type="button"
            onClick={() => setScale((s) => Math.max(0.5, s - 0.2))}
            className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm border border-[rgba(25,24,22,0.1)] bg-app-surface text-ink-secondary transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
            aria-label="Zoom out"
          >
            <ZoomOut className="h-3.5 w-3.5" strokeWidth={1.5} />
          </button>
          <span className="min-w-[3.25rem] text-center font-mono text-phi-xs tabular-nums text-ink-secondary">
            {Math.round(scale * 100)}%
          </span>
          <button
            type="button"
            onClick={() => setScale((s) => Math.min(3, s + 0.2))}
            className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm border border-[rgba(25,24,22,0.1)] bg-app-surface text-ink-secondary transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
            aria-label="Zoom in"
          >
            <ZoomIn className="h-3.5 w-3.5" strokeWidth={1.5} />
          </button>
        </div>

        <button
          type="button"
          onClick={handlePageVoiceover}
          disabled={pageVoiceGenerating || !currentPageText}
          className="inline-flex h-phi-ctrl-sm items-center gap-phi-2 rounded-phi-sm border border-[rgba(25,24,22,0.12)] bg-app-surface px-phi-3 text-phi-xs font-medium text-ink-primary transition-colors duration-phi-fast hover:bg-paper-200 disabled:cursor-not-allowed disabled:opacity-50"
          title={currentPageText ? 'Read this page aloud' : 'Waiting for page text'}
        >
          {pageVoiceGenerating ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" strokeWidth={1.5} />
              <span>Building audio</span>
            </>
          ) : (
            <>
              <Volume2 className="h-3.5 w-3.5 text-ink-muted" strokeWidth={1.5} />
              <span>Voiceover</span>
            </>
          )}
        </button>
      </div>

      {/* Voiceover error notice */}
      {voiceoverError && (
        <div
          role="alert"
          className="flex items-center justify-between gap-phi-3 border-b border-semantic-negative/25 bg-semantic-negativeBg px-phi-4 py-phi-2 text-phi-xs text-semantic-negative"
        >
          <span>Voiceover failed: {voiceoverError}</span>
          <button
            type="button"
            onClick={() => setVoiceoverError(null)}
            className="font-medium underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* PDF Reading Desk */}
      <div ref={deskRef} className="relative flex flex-1 justify-center overflow-auto p-phi-4 scrollbar-thin">
        {pdfLoadError ? (
          <div className="my-auto flex max-w-phi-modal-sm flex-col items-center justify-center gap-phi-2 rounded-phi-lg border border-semantic-negative/25 bg-semantic-negativeBg p-phi-5 text-center">
            <p className="text-phi-sm font-medium text-semantic-negative">Could not load this PDF</p>
            <p className="text-phi-xs text-ink-secondary">{pdfLoadError}</p>
          </div>
        ) : !pdfFile ? (
          <div className="my-auto flex items-center gap-phi-2 text-phi-sm text-ink-secondary">
            <Loader2 className="h-4 w-4 animate-spin text-ink-muted" strokeWidth={1.5} />
            <span>Loading sheet</span>
          </div>
        ) : (
          <Document
            file={pdfFile}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={
              <div className="flex items-center gap-phi-2 py-phi-6 text-phi-sm text-ink-secondary">
                <Loader2 className="h-4 w-4 animate-spin text-ink-muted" strokeWidth={1.5} />
                <span>Rendering page</span>
              </div>
            }
            error={
              <div className="rounded-phi-md border border-semantic-negative/25 bg-semantic-negativeBg p-phi-4 text-phi-sm text-semantic-negative">
                Unable to load the protected PDF file.
              </div>
            }
          >
            <Page
              pageNumber={pageNumber}
              width={fittedPageWidth}
              scale={scale}
              renderTextLayer={true}
              renderAnnotationLayer={true}
              onLoadSuccess={handlePageLoadSuccess}
              className="rounded-phi-xs bg-white shadow-sheet ring-1 ring-[rgba(25,24,22,0.08)]"
            />
          </Document>
        )}

        {/* Floating Selection Action Bar */}
        {selectedText && menuPosition && (
          <div
            className="fixed z-50 flex items-center gap-phi-1 rounded-phi-md border border-[rgba(25,24,22,0.16)] bg-ink-primary p-phi-1 text-paper-50 shadow-float"
            onMouseDown={(event) => event.preventDefault()}
            style={{
              left: `${menuPosition.x}px`,
              top: `${menuPosition.y}px`,
              transform: 'translate(-50%, -100%)',
            }}
          >
            <button
              type="button"
              onClick={handleAskLLM}
              className="flex items-center gap-phi-2 rounded-phi-sm bg-accent px-phi-3 py-phi-1 text-phi-xs font-medium text-white transition-colors duration-phi-fast hover:bg-accent-hover"
              title="Ask about this excerpt"
            >
              <MessageSquare className="h-3.5 w-3.5" strokeWidth={1.5} />
              Ask
            </button>

            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-phi-2 rounded-phi-sm px-phi-3 py-phi-1 text-phi-xs font-medium text-paper-100 transition-colors duration-phi-fast hover:bg-white/10"
              title="Copy to clipboard"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-[#4cc38a]" strokeWidth={1.5} />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" strokeWidth={1.5} />
                  Copy
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleGenerateVoice}
              disabled={generating}
              className="flex items-center gap-phi-2 rounded-phi-sm px-phi-3 py-phi-1 text-phi-xs font-medium text-paper-100 transition-colors duration-phi-fast hover:bg-white/10 disabled:opacity-50"
              title="Read excerpt aloud"
            >
              {generating ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.5} />
                  Generating
                </>
              ) : (
                <>
                  <Volume2 className="h-3.5 w-3.5" strokeWidth={1.5} />
                  Voice
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default SimplePDFViewer;
