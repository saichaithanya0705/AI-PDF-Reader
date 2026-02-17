import React, { useState } from 'react';
import { ExternalLink, FileText, Zap, RefreshCw, Loader2, MessageCircle, Lightbulb } from 'lucide-react';
import { usePDF } from '../context/PDFContext';

interface RecommendationsPanelProps {
  onOpenInsights?: () => void;
}

const RecommendationsPanel: React.FC<RecommendationsPanelProps> = ({ onOpenInsights }) => {
  const { relatedSections, currentDocument, getRelatedSections } = usePDF();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleSectionClick = (section: any) => {
    // Navigate to the specific document and page
    if (section.documentId !== currentDocument?.id) {
      // Cross-document navigation
      console.log('Navigating to different document:', section.documentId, 'page:', section.page);
      // TODO: Implement cross-document navigation
    } else {
      // Same document navigation
      console.log('Navigating to page:', section.page);
      // TODO: Implement page navigation within current document
    }
  };

  const handleRefresh = async () => {
    if (!currentDocument) return;

    setIsRefreshing(true);
    try {
      await getRelatedSections(currentDocument.id, 1); // Refresh for current page
    } catch (error) {
      console.error('Error refreshing recommendations:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-cyan-400" />
            <h3 className="font-semibold text-white">Smart Recommendations</h3>
          </div>
          <div className="flex items-center gap-1">
            {onOpenInsights && (
              <button
                onClick={onOpenInsights}
                className="p-1 text-slate-400 hover:text-yellow-400 transition-colors group"
                title="Open AI Insights (+5 points)"
              >
                <div className="relative">
                  <Lightbulb className="w-4 h-4 group-hover:animate-pulse" />
                  <div className="absolute -top-1 -right-1 w-2 h-2 bg-yellow-400 rounded-full animate-ping opacity-75"></div>
                </div>
              </button>
            )}
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="p-1 text-slate-400 hover:text-cyan-400 transition-colors disabled:opacity-50"
              title="Refresh recommendations"
            >
              {isRefreshing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-400">
            AI-powered connections across your documents
          </p>
          {onOpenInsights && (
            <button
              onClick={onOpenInsights}
              className="text-xs text-yellow-400/80 hover:text-yellow-400 transition-colors flex items-center gap-1"
            >
              <MessageCircle className="w-3 h-3" />
              <span>Get Insights</span>
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {relatedSections.length === 0 ? (
          <div className="text-center text-slate-400 py-8">
            <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No recommendations yet</p>
            <p className="text-xs mt-1">Start reading to see related content</p>
          </div>
        ) : (
          relatedSections.map((section) => (
            <div
              key={section.id}
              onClick={() => handleSectionClick(section)}
              className="group relative cursor-pointer"
            >
              <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-400/20 to-purple-600/20 rounded-lg blur opacity-0 group-hover:opacity-100 transition-opacity duration-200"></div>
              <div className="relative bg-slate-800/50 hover:bg-slate-800/80 rounded-lg p-4 border border-slate-700 hover:border-slate-600 transition-all duration-200">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h4 className="font-medium text-white text-sm line-clamp-2 group-hover:text-cyan-400 transition-colors">
                    {section.title}
                  </h4>
                  <div className="flex items-center gap-1">
                    <div className={`w-2 h-2 rounded-full ${
                      section.relevance > 0.9 ? 'bg-green-400' :
                      section.relevance > 0.8 ? 'bg-yellow-400' : 'bg-orange-400'
                    }`} />
                    <span className="text-xs text-slate-400">
                      {Math.round(section.relevance * 100)}%
                    </span>
                  </div>
                </div>
                
                <p className="text-xs text-slate-400 mb-3 line-clamp-3">
                  {section.snippet}
                </p>
                
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 text-slate-500">
                    <FileText className="w-3 h-3" />
                    <span className="truncate max-w-32">{section.documentName}</span>
                  </div>
                  <div className="flex items-center gap-1 text-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity">
                    <span>Page {section.page}</span>
                    <ExternalLink className="w-3 h-3" />
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="p-4 border-t border-slate-700">
        <div className="text-xs text-slate-400 text-center">
          <span className="bg-slate-800 px-2 py-1 rounded">
            ⚡ Powered by CPU-based AI
          </span>
        </div>
      </div>
    </div>
  );
};

export default RecommendationsPanel;