import React, { useState } from 'react';
import { Copy, MessageCircle, X, Check, ExternalLink, Lightbulb, Loader2, Search } from 'lucide-react';
import { usePDF } from '../context/usePDF';
import { analyzeTextSelection, askGeminiSelection } from '../lib/api';

interface TextSelectionTooltipProps {
  text: string;
  position: { x: number; y: number };
  isOnline: boolean;
  documentId?: string;
  currentPage?: number;
  onClose: () => void;
}

interface AnalysisSection {
  document_name?: string;
  snippet?: string;
  relevance_score?: number;
}

interface InsightBulb {
  title?: string;
  content?: string;
}

interface SelectionAnalysis {
  text_insights?: {
    explanation?: string;
  };
  cross_document_sections?: AnalysisSection[];
  insights_bulb?: InsightBulb[];
  metadata?: {
    total_cross_document?: number;
  };
}

const TextSelectionTooltip: React.FC<TextSelectionTooltipProps> = ({
  text,
  position,
  isOnline,
  documentId,
  currentPage = 1,
  onClose,
}) => {
  const { askGPT } = usePDF();
  const [showGPTResponse, setShowGPTResponse] = useState(false);
  const [gptResponse, setGPTResponse] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [analysisData, setAnalysisData] = useState<SelectionAnalysis | null>(null);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [geminiResponse, setGeminiResponse] = useState<string>('');
  const [showGeminiResponse, setShowGeminiResponse] = useState(false);
  const [isGeminiLoading, setIsGeminiLoading] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => {
      setCopied(false);
      onClose();
    }, 1500);
  };

  const handleAskGPT = async () => {
    if (!isOnline) return;
    setIsLoading(true);
    try {
      const response = await askGPT(text, 'Current document context');
      setGPTResponse(response);
      setShowGPTResponse(true);
    } catch (error) {
      console.error('Failed to get explanation:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyzeSelection = async () => {
    if (!isOnline || !documentId) return;
    setIsLoading(true);
    try {
      const persona = localStorage.getItem('lastPersona') || 'Student';
      const job = localStorage.getItem('lastJob') || 'Learning and Research';
      const data = await analyzeTextSelection(text, documentId, currentPage, persona, job, true);
      setAnalysisData(data as SelectionAnalysis);
      setShowAnalysis(true);
    } catch (error) {
      console.error('Failed to analyze selection:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAskGemini = async () => {
    if (!documentId) return;
    setIsGeminiLoading(true);
    setShowGeminiResponse(true);
    try {
      const data = await askGeminiSelection(documentId, text, currentPage, 500);
      const explanation =
        data && typeof data === 'object' ? (data as { explanation?: unknown }).explanation : undefined;
      setGeminiResponse(typeof explanation === 'string' ? explanation : 'No explanation available.');
    } catch {
      setGeminiResponse('Could not analyze this excerpt right now. Try again.');
    } finally {
      setIsGeminiLoading(false);
    }
  };

  return (
    <div
      className="pointer-events-auto fixed z-50"
      style={{
        left: Math.max(12, Math.min(position.x - 120, window.innerWidth - 260)),
        top: Math.max(12, position.y - 10),
      }}
    >
      {!showGPTResponse && !showAnalysis && !showGeminiResponse ? (
        <div className="flex items-center gap-phi-1 overflow-hidden rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-ink-primary p-phi-1 text-paper-50 shadow-float">
          <button
            type="button"
            onClick={handleCopy}
            disabled={copied}
            className="flex items-center gap-phi-2 rounded-phi-sm px-phi-3 py-phi-1 text-phi-xs font-medium transition-colors duration-phi-fast hover:bg-white/10"
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

          {isOnline && (
            <button
              type="button"
              onClick={handleAskGPT}
              disabled={isLoading}
              className="flex items-center gap-phi-2 rounded-phi-sm px-phi-3 py-phi-1 text-phi-xs font-medium transition-colors duration-phi-fast hover:bg-white/10"
            >
              {isLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.5} />
              ) : (
                <MessageCircle className="h-3.5 w-3.5" strokeWidth={1.5} />
              )}
              Explain
            </button>
          )}

          {isOnline && documentId && (
            <button
              type="button"
              onClick={handleAskGemini}
              disabled={isGeminiLoading}
              className="flex items-center gap-phi-2 rounded-phi-sm px-phi-3 py-phi-1 text-phi-xs font-medium transition-colors duration-phi-fast hover:bg-white/10"
            >
              {isGeminiLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.5} />
              ) : (
                <Lightbulb className="h-3.5 w-3.5" strokeWidth={1.5} />
              )}
              Summarize
            </button>
          )}

          {isOnline && documentId && (
            <button
              type="button"
              onClick={handleAnalyzeSelection}
              disabled={isLoading}
              className="flex items-center gap-phi-2 rounded-phi-sm px-phi-3 py-phi-1 text-phi-xs font-medium transition-colors duration-phi-fast hover:bg-white/10"
            >
              {isLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.5} />
              ) : (
                <Search className="h-3.5 w-3.5" strokeWidth={1.5} />
              )}
              Find related
            </button>
          )}

          <button
            type="button"
            onClick={onClose}
            className="rounded-phi-sm p-phi-1 text-paper-300 transition-colors duration-phi-fast hover:bg-white/10 hover:text-white"
            aria-label="Close selection toolbar"
          >
            <X className="h-3.5 w-3.5" strokeWidth={1.5} />
          </button>
        </div>
      ) : (
        <div className="w-phi-chat max-w-phi-modal-sm rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-app-surface p-phi-4 text-ink-primary shadow-float">
          <div className="flex items-center justify-between border-b border-[rgba(25,24,22,0.08)] pb-phi-2">
            <span className="text-phi-xs font-medium text-ink-primary">
              {showGPTResponse
                ? 'Passage explanation'
                : showGeminiResponse
                  ? 'Contextual summary'
                  : 'Cross-document matches'}
            </span>
            <button
              type="button"
              onClick={onClose}
              className="rounded-phi-xs p-phi-1 text-ink-muted hover:bg-paper-200 hover:text-ink-primary"
              aria-label="Close"
            >
              <X className="h-3.5 w-3.5" strokeWidth={1.5} />
            </button>
          </div>

          <div className="mt-phi-3 max-h-64 space-y-phi-3 overflow-y-auto text-phi-xs leading-phi text-ink-secondary scrollbar-thin">
            {showGPTResponse && <p>{gptResponse}</p>}

            {showGeminiResponse &&
              (isGeminiLoading ? (
                <div className="flex items-center gap-phi-2 text-ink-muted">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.5} />
                  Analyzing excerpt
                </div>
              ) : (
                <p>{geminiResponse}</p>
              ))}

            {showAnalysis && analysisData && (
              <>
                {analysisData.text_insights?.explanation && (
                  <p className="text-ink-primary">{analysisData.text_insights.explanation}</p>
                )}

                {analysisData.cross_document_sections &&
                  analysisData.cross_document_sections.length > 0 && (
                    <div className="space-y-phi-2 border-t border-[rgba(25,24,22,0.08)] pt-phi-2">
                      <p className="flex items-center gap-phi-2 font-medium text-ink-primary">
                        <ExternalLink className="h-3.5 w-3.5 text-ink-muted" strokeWidth={1.5} />
                        Related files ({analysisData.cross_document_sections.length})
                      </p>
                      {analysisData.cross_document_sections.slice(0, 3).map((section, index) => (
                        <div key={index} className="folio-mark pl-phi-3">
                          <div className="flex items-center justify-between gap-phi-2">
                            <span className="truncate font-medium text-ink-primary">
                              {section.document_name}
                            </span>
                            <span className="font-mono text-phi-2xs tabular-nums text-accent-ink">
                              {((section.relevance_score ?? 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                          <p className="mt-phi-1 line-clamp-2 text-ink-secondary">{section.snippet}</p>
                        </div>
                      ))}
                    </div>
                  )}

                {analysisData.insights_bulb && analysisData.insights_bulb.length > 0 && (
                  <div className="space-y-phi-2 border-t border-[rgba(25,24,22,0.08)] pt-phi-2">
                    {analysisData.insights_bulb.slice(0, 2).map((insight, index) => (
                      <div key={index}>
                        <p className="font-medium text-ink-primary">{insight.title || 'Note'}</p>
                        <p className="mt-phi-1 text-ink-secondary">{insight.content || ''}</p>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          <div className="mt-phi-3 flex items-center justify-between border-t border-[rgba(25,24,22,0.08)] pt-phi-2 text-phi-xs">
            <span className="font-mono text-phi-2xs tabular-nums text-ink-muted">
              Page {currentPage}
            </span>
            <button
              type="button"
              onClick={() => {
                setShowGPTResponse(false);
                setShowGeminiResponse(false);
                setShowAnalysis(false);
              }}
              className="font-medium text-accent-ink hover:underline"
            >
              Back
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TextSelectionTooltip;
