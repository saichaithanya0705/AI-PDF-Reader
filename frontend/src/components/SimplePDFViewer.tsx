import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import type { PDFPageProxy } from 'pdfjs-dist/types/src/display/api';
import { PDFDocument } from '../context/PDFContext';
import { API_URL } from '../config';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Loader2, MessageSquare, Copy, Volume2, Check } from 'lucide-react';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';

// Configure PDF.js worker - use CDN for pdfjs-dist 3.11.174
pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js`;

interface SimplePDFViewerProps {
  document: PDFDocument;
  onPageChange: (page: number) => void;
  onTextSelection?: (text: string, page: number) => void;
  onAskLLM?: (text: string, page: number) => void;
}

interface SelectionMenuPosition {
  x: number;
  y: number;
}

const SimplePDFViewer: React.FC<SimplePDFViewerProps> = ({ document: pdfDocument, onPageChange, onTextSelection, onAskLLM }) => {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.2);
  const [selectedText, setSelectedText] = useState<string>('');
  const [menuPosition, setMenuPosition] = useState<SelectionMenuPosition | null>(null);
  const [copied, setCopied] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [pageVoiceGenerating, setPageVoiceGenerating] = useState(false);
  const [currentPageText, setCurrentPageText] = useState<string>('');
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const pdfUrl = pdfDocument.url?.startsWith('http') ? pdfDocument.url : `${API_URL}${pdfDocument.url}`;

  useEffect(() => {
    return () => {
      currentAudio?.pause();
    };
  }, [currentAudio]);

  const handlePageLoadSuccess = useCallback(async (page: PDFPageProxy) => {
    try {
      const textContent = await page.getTextContent();
      const combinedText = textContent.items
        .map((item: any) => (typeof item.str === 'string' ? item.str : ''))
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
      const response = await fetch(`${API_URL}/api/generate-audio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          document_id: pdfDocument.id,
          page_number: pageNumber,
        }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Failed to generate audio');
      }

      const data = await response.json();
      if (data.audio_url) {
        currentAudio?.pause();
        const audio = new Audio(`${API_URL}${data.audio_url}`);
        setCurrentAudio(audio);
        await audio.play();
      }
    },
    [API_URL, currentAudio, pageNumber, pdfDocument.id]
  );

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
  }, []);

  // Handle text selection
  useEffect(() => {
    const handleSelection = () => {
      const selection = window.getSelection();
      const text = selection?.toString().trim();
      
      if (text && text.length > 0) {
        setSelectedText(text);
        
        // Get selection position for floating menu
        const range = selection?.getRangeAt(0);
        const rect = range?.getBoundingClientRect();
        
        if (rect) {
          setMenuPosition({
            x: rect.left + rect.width / 2,
            y: rect.top - 10
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
    // Call the new onAskLLM callback if provided
    if (onAskLLM) {
      onAskLLM(selectedText, pageNumber);
    }
    // Also call the legacy callback for backwards compatibility
    if (onTextSelection) {
      onTextSelection(selectedText, pageNumber);
    }
    // Clear selection after asking
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
    <div className="flex flex-col h-full bg-slate-900 text-white" ref={containerRef}>
      {/* Top Navigation Bar */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <button onClick={goToPrevPage} disabled={pageNumber <= 1} className="p-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 transition-colors">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm font-medium">{pageNumber} / {numPages}</span>
          <button onClick={goToNextPage} disabled={pageNumber >= numPages} className="p-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 transition-colors">
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setScale(s => Math.max(0.5, s - 0.2))} className="p-2 rounded-lg bg-slate-700 hover:bg-slate-600 transition-colors">
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-sm font-medium min-w-[3rem] text-center">{Math.round(scale * 100)}%</span>
          <button onClick={() => setScale(s => Math.min(3, s + 0.2))} className="p-2 rounded-lg bg-slate-700 hover:bg-slate-600 transition-colors">
            <ZoomIn className="w-4 h-4" />
          </button>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handlePageVoiceover}
            disabled={pageVoiceGenerating || !currentPageText}
            className="flex items-center gap-2 rounded-full bg-purple-600 px-2.5 py-2 text-xs font-medium text-white transition hover:bg-purple-500 disabled:cursor-not-allowed disabled:opacity-60 sm:px-3 sm:text-sm"
            title={currentPageText ? 'Generate voiceover for this page' : 'Page text is loading'}
          >
            {pageVoiceGenerating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Building voiceover
              </>
            ) : (
              <>
                <Volume2 className="h-4 w-4" />
                Voiceover
              </>
            )}
          </button>
        </div>
      </div>

      {/* PDF Content Area */}
      <div className="flex-1 overflow-auto bg-slate-950 flex justify-center p-4 relative">
        <Document 
          file={pdfUrl} 
          onLoadSuccess={onDocumentLoadSuccess} 
          loading={<Loader2 className="w-8 h-8 animate-spin text-cyan-400" />}
        >
          <Page 
            pageNumber={pageNumber} 
            scale={scale} 
            renderTextLayer={true} 
            renderAnnotationLayer={true} 
            onLoadSuccess={handlePageLoadSuccess}
            className="shadow-2xl"
          />
        </Document>

        {/* Floating Selection Menu */}
        {selectedText && menuPosition && (
          <div
            className="fixed z-50 bg-slate-800 rounded-lg shadow-2xl border border-slate-700 p-2 flex items-center gap-2 animate-in fade-in slide-in-from-top-2 duration-200"
            style={{
              left: `${menuPosition.x}px`,
              top: `${menuPosition.y}px`,
              transform: 'translate(-50%, -100%)',
            }}
          >
            {/* Ask LLM Button */}
            <button
              onClick={handleAskLLM}
              className="flex items-center gap-2 px-3 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors"
              title="Ask AI about this text"
            >
              <MessageSquare className="w-4 h-4" />
              Ask LLM
            </button>

            {/* Copy Button */}
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-3 py-2 rounded-md bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium transition-colors"
              title="Copy to clipboard"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 text-green-400" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  Copy
                </>
              )}
            </button>

            {/* Generate Voice Button */}
            <button
              onClick={handleGenerateVoice}
              disabled={generating}
              className="flex items-center gap-2 px-3 py-2 rounded-md bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 disabled:opacity-50 text-white text-sm font-medium transition-colors"
              title="Generate audio for this text"
            >
              {generating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Volume2 className="w-4 h-4" />
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
