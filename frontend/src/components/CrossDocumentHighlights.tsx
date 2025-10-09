import React from 'react';
import { ExternalLink, Brain, Star, ArrowRight } from 'lucide-react';
import { RelatedSection } from '../context/PDFContext';

interface CrossDocumentHighlightsProps {
  crossDocumentSections: RelatedSection[];
  onOpenDocument: (documentId: string, page?: number) => void;
  currentPage: number;
  documentId: string;
}

const CrossDocumentHighlights: React.FC<CrossDocumentHighlightsProps> = ({
  crossDocumentSections,
  onOpenDocument,
  currentPage,
  documentId
}) => {
  const getRelevanceColor = (relevance: number) => {
    if (relevance >= 0.8) return 'border-green-400 bg-green-400/10';
    if (relevance >= 0.6) return 'border-yellow-400 bg-yellow-400/10';
    return 'border-orange-400 bg-orange-400/10';
  };

  const getRelevanceIcon = (relevance: number) => {
    if (relevance >= 0.8) return <Star className="w-4 h-4 text-green-400" />;
    if (relevance >= 0.6) return <Brain className="w-4 h-4 text-yellow-400" />;
    return <ExternalLink className="w-4 h-4 text-orange-400" />;
  };

  const handleSectionClick = (section: RelatedSection) => {
    console.log('🔗 Opening cross-document section:', section);
    onOpenDocument(section.documentId, section.page);
  };

  if (!crossDocumentSections || crossDocumentSections.length === 0) {
    return null;
  }

  return (
    <div className="fixed top-20 right-4 w-80 max-h-96 overflow-y-auto z-50">
      <div className="bg-slate-900/95 backdrop-blur-lg rounded-xl border border-slate-700 shadow-2xl">
        {/* Header */}
        <div className="p-4 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-lg">
              <ExternalLink className="w-4 h-4 text-purple-400" />
            </div>
            <h3 className="text-sm font-semibold text-white">Related Documents</h3>
            <span className="ml-auto text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded-full">
              {crossDocumentSections.length}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            AI found {crossDocumentSections.length} relevant sections in other documents
          </p>
        </div>

        {/* Cross-document sections */}
        <div className="p-3 space-y-2">
          {crossDocumentSections.slice(0, 3).map((section, index) => {
            const relevance = section.enhanced_relevance || section.relevance;
            
            return (
              <div
                key={section.id}
                onClick={() => handleSectionClick(section)}
                className={`p-3 rounded-lg border-2 cursor-pointer transition-all duration-200 hover:scale-[1.02] hover:shadow-lg ${getRelevanceColor(relevance)} hover:border-opacity-60`}
              >
                {/* Section header */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-1.5">
                    {getRelevanceIcon(relevance)}
                    <span className="text-xs font-medium text-white">
                      #{index + 1}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-slate-400">
                      {(relevance * 100).toFixed(0)}%
                    </span>
                    <ArrowRight className="w-3 h-3 text-slate-400" />
                  </div>
                </div>

                {/* Section title */}
                <h4 className="text-sm font-medium text-white mb-1 line-clamp-1">
                  {section.title}
                </h4>

                {/* Section snippet */}
                <p className="text-xs text-slate-300 mb-2 line-clamp-2">
                  {section.snippet}
                </p>

                {/* Document info */}
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">
                    Page {section.page}
                  </span>
                  <span className="text-purple-400 font-medium">
                    Other Document
                  </span>
                </div>

                {/* Intelligence explanation */}
                {section.intelligence_explanation && (
                  <div className="mt-2 pt-2 border-t border-slate-700/50">
                    <p className="text-xs text-cyan-400 italic">
                      {section.intelligence_explanation}
                    </p>
                  </div>
                )}

                {/* Hover effect overlay */}
                <div className="absolute inset-0 bg-gradient-to-r from-purple-500/10 to-pink-500/10 rounded-lg opacity-0 hover:opacity-100 transition-opacity duration-200 pointer-events-none" />
              </div>
            );
          })}
        </div>

        {/* Footer */}
        {crossDocumentSections.length > 3 && (
          <div className="p-3 border-t border-slate-700 text-center">
            <span className="text-xs text-slate-400">
              +{crossDocumentSections.length - 3} more related sections
            </span>
          </div>
        )}
      </div>

      {/* Floating action hint */}
      <div className="mt-2 text-center">
        <div className="inline-flex items-center gap-1 px-3 py-1 bg-slate-800/80 backdrop-blur rounded-full text-xs text-slate-400">
          <ExternalLink className="w-3 h-3" />
          Click to open related document
        </div>
      </div>
    </div>
  );
};

export default CrossDocumentHighlights;

