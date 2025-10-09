import React, { useState } from 'react';
import { Copy, MessageCircle, X, Check, Brain, ExternalLink, Lightbulb, Loader2, Sparkles } from 'lucide-react';
import { usePDF } from '../context/PDFContext';

interface TextSelectionTooltipProps {
  text: string;
  position: { x: number; y: number };
  isOnline: boolean;
  documentId?: string;
  currentPage?: number;
  onClose: () => void;
}

const TextSelectionTooltip: React.FC<TextSelectionTooltipProps> = ({
  text,
  position,
  isOnline,
  documentId,
  currentPage = 1,
  onClose
}) => {
  const { askGPT } = usePDF();
  const [showGPTResponse, setShowGPTResponse] = useState(false);
  const [gptResponse, setGPTResponse] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [analysisData, setAnalysisData] = useState<any>(null);
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
      console.error('Failed to get GPT response:', error);
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

      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000'}/api/text-selection-analysis`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          selected_text: text,
          document_id: documentId,
          page: currentPage,
          persona,
          job,
          include_cross_document: true
        })
      });

      if (!response.ok) {
        throw new Error('Failed to analyze selection');
      }

      const data = await response.json();
      setAnalysisData(data);
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
      // Get context around the selected text for better accuracy
      const response = await fetch('/api/ask-gemini-selection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: documentId,
          selected_text: text,
          page: currentPage,
          context_chars: 500 // Get 500 chars before and after for context
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get Gemini response');
      }

      const data = await response.json();
      setGeminiResponse(data.explanation || 'No explanation available');
    } catch (error) {
      console.error('Failed to ask Gemini:', error);
      setGeminiResponse('Sorry, I could not analyze this text at the moment. Please try again.');
    } finally {
      setIsGeminiLoading(false);
    }
  };

  return (
    <div
      className="fixed z-50 pointer-events-auto"
      style={{
        left: Math.max(10, Math.min(position.x - 120, window.innerWidth - 250)),
        top: Math.max(10, position.y - 10),
      }}
    >
      <div className="relative">
        {!showGPTResponse && !showAnalysis && !showGeminiResponse ? (
          // Selection Actions
          <div className="bg-slate-900/95 backdrop-blur border border-slate-600 rounded-lg shadow-xl overflow-hidden">
            <div className="flex items-center">
              <button
                onClick={handleCopy}
                className="flex items-center gap-2 px-4 py-3 hover:bg-slate-800 transition-colors text-white"
                disabled={copied}
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4 text-green-400" />
                    <span className="text-sm text-green-400">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 text-slate-400" />
                    <span className="text-sm">Copy Text</span>
                  </>
                )}
              </button>
              
              {isOnline && (
                <button
                  onClick={handleAskGPT}
                  disabled={isLoading}
                  className="flex items-center gap-2 px-4 py-3 hover:bg-slate-800 transition-colors text-white border-l border-slate-600"
                >
                  {isLoading ? (
                    <div className="animate-spin w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full" />
                  ) : (
                    <MessageCircle className="w-4 h-4 text-cyan-400" />
                  )}
                  <span className="text-sm">Ask GPT</span>
                </button>
              )}

              {isOnline && documentId && (
                <button
                  onClick={handleAskGemini}
                  disabled={isGeminiLoading}
                  className="flex items-center gap-2 px-4 py-3 hover:bg-slate-800 transition-colors text-white border-l border-slate-600"
                >
                  {isGeminiLoading ? (
                    <Loader2 className="w-4 h-4 text-purple-400 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4 text-purple-400" />
                  )}
                  <span className="text-sm">Ask Gemini</span>
                </button>
              )}

              {isOnline && documentId && (
                <button
                  onClick={handleAnalyzeSelection}
                  disabled={isLoading}
                  className="flex items-center gap-2 px-4 py-3 hover:bg-slate-800 transition-colors text-white border-l border-slate-600"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                  ) : (
                    <Brain className="w-4 h-4 text-purple-400" />
                  )}
                  <span className="text-sm">Find Related</span>
                </button>
              )}
              
              <button
                onClick={onClose}
                className="p-3 hover:bg-slate-800 transition-colors text-slate-400 hover:text-white border-l border-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : showGPTResponse ? (
          // GPT Response
          <div className="bg-slate-900/95 backdrop-blur border border-slate-600 rounded-lg shadow-xl p-4 max-w-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <MessageCircle className="w-4 h-4 text-cyan-400" />
                <span className="text-sm font-medium text-white">GPT Explanation</span>
              </div>
              <button
                onClick={onClose}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-sm text-slate-300 leading-relaxed mb-3">
              {gptResponse}
            </div>

            <div className="flex justify-between items-center pt-3 border-t border-slate-700">
              <span className="text-xs text-slate-400">Powered by AI</span>
              <button
                onClick={() => setShowGPTResponse(false)}
                className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
              >
                Back
              </button>
            </div>
          </div>
        ) : showGeminiResponse ? (
          // Gemini Response
          <div className="bg-slate-900/95 backdrop-blur border border-slate-600 rounded-lg shadow-xl p-4 max-w-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <span className="text-sm font-medium text-white">Gemini Explanation</span>
              </div>
              <button
                onClick={onClose}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-sm text-slate-300 leading-relaxed mb-3">
              {isGeminiLoading ? (
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                  <span>Gemini is analyzing...</span>
                </div>
              ) : (
                geminiResponse
              )}
            </div>

            <div className="flex justify-between items-center pt-3 border-t border-slate-700">
              <span className="text-xs text-slate-400">Powered by Gemini AI</span>
              <button
                onClick={() => setShowGeminiResponse(false)}
                className="text-xs text-purple-400 hover:text-purple-300 transition-colors"
              >
                Back
              </button>
            </div>
          </div>
        ) : showAnalysis && analysisData ? (
          // Analysis Results
          <div className="bg-slate-900/95 backdrop-blur border border-slate-600 rounded-lg shadow-xl p-4 max-w-md">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-purple-400" />
                <span className="text-sm font-medium text-white">Cross-Document Analysis</span>
              </div>
              <button
                onClick={onClose}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 max-h-64 overflow-y-auto">
              {/* Text Insights */}
              {analysisData.text_insights && (
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <h4 className="text-xs font-medium text-purple-400 mb-2">Analysis</h4>
                  <p className="text-xs text-slate-300">{analysisData.text_insights.explanation}</p>
                </div>
              )}

              {/* Cross-Document Sections */}
              {analysisData.cross_document_sections && analysisData.cross_document_sections.length > 0 && (
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <h4 className="text-xs font-medium text-green-400 mb-2 flex items-center gap-1">
                    <ExternalLink className="w-3 h-3" />
                    Related Documents ({analysisData.cross_document_sections.length})
                  </h4>
                  <div className="space-y-2">
                    {analysisData.cross_document_sections.slice(0, 3).map((section: any, index: number) => (
                      <div key={index} className="text-xs">
                        <div className="text-slate-400 font-medium">{section.document_name}</div>
                        <div className="text-slate-300">{section.snippet}</div>
                        <div className="text-green-400 text-xs">Relevance: {(section.relevance_score * 100).toFixed(0)}%</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Insights Bulb */}
              {analysisData.insights_bulb && analysisData.insights_bulb.length > 0 && (
                <div className="bg-slate-800/50 rounded-lg p-3">
                  <h4 className="text-xs font-medium text-amber-400 mb-2 flex items-center gap-1">
                    <Lightbulb className="w-3 h-3" />
                    AI Insights
                  </h4>
                  <div className="space-y-2">
                    {analysisData.insights_bulb.slice(0, 2).map((insight: any, index: number) => (
                      <div key={index} className="text-xs">
                        <div className="text-amber-300 font-medium">{insight.title}</div>
                        <div className="text-slate-300">{insight.content}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-between items-center pt-3 border-t border-slate-700">
              <span className="text-xs text-slate-400">
                Found {analysisData.metadata?.total_cross_document || 0} related sections
              </span>
              <button
                onClick={() => setShowAnalysis(false)}
                className="text-xs text-purple-400 hover:text-purple-300 transition-colors"
              >
                Back
              </button>
            </div>
          </div>
        ) : null}
        
        {/* Arrow pointing to selection */}
        <div className="absolute top-full left-1/2 transform -translate-x-1/2">
          <div className="w-3 h-3 bg-slate-900 border-b border-r border-slate-600 transform rotate-45"></div>
        </div>
      </div>
    </div>
  );
};

export default TextSelectionTooltip;