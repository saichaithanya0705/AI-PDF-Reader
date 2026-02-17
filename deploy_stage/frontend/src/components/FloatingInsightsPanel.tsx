import React, { useState, useEffect, useRef } from 'react';
import { Lightbulb, Brain, AlertTriangle, Link, X, Minimize2, Maximize2, MessageCircle, Target, Search, Clock, TrendingUp, Key, Info } from 'lucide-react';
import { usePDF } from '../context/PDFContext';

interface FloatingInsightsPanelProps {
  isVisible: boolean;
  onClose: () => void;
  position?: { x: number; y: number };
}

const FloatingInsightsPanel: React.FC<FloatingInsightsPanelProps> = ({ 
  isVisible, 
  onClose, 
  position = { x: 100, y: 100 } 
}) => {
  const { insights, isOnline, currentDocument, getInsights } = usePDF();
  const [isMinimized, setIsMinimized] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [panelPosition, setPanelPosition] = useState(position);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isVisible && currentDocument && insights.length === 0) {
      // Auto-load insights when panel opens
      getInsights(currentDocument.id, 1, 'Student', 'Research');
    }
  }, [isVisible, currentDocument]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget || (e.target as HTMLElement).classList.contains('drag-handle')) {
      setIsDragging(true);
      const rect = panelRef.current?.getBoundingClientRect();
      if (rect) {
        setDragOffset({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        });
      }
    }
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        setPanelPosition({
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragOffset]);

  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'key-takeaway':
        return <Key className="w-4 h-4 text-yellow-400" />;
      case 'key-insight':
        return <Brain className="w-4 h-4 text-cyan-400" />;
      case 'did-you-know':
        return <Info className="w-4 h-4 text-blue-400" />;
      case 'counterpoint':
        return <AlertTriangle className="w-4 h-4 text-orange-400" />;
      case 'connection':
        return <Link className="w-4 h-4 text-green-400" />;
      case 'practical-tip':
        return <Target className="w-4 h-4 text-purple-400" />;
      case 'deep-dive':
        return <Search className="w-4 h-4 text-indigo-400" />;
      case 'historical-context':
        return <Clock className="w-4 h-4 text-amber-400" />;
      case 'future-implications':
        return <TrendingUp className="w-4 h-4 text-cyan-400" />;
      default:
        return <Lightbulb className="w-4 h-4 text-yellow-400" />;
    }
  };

  const getInsightColor = (type: string) => {
    switch (type) {
      case 'key-takeaway':
        return 'from-yellow-400/20 to-yellow-600/20 border-yellow-400/30';
      case 'key-insight':
        return 'from-cyan-400/20 to-cyan-600/20 border-cyan-400/30';
      case 'did-you-know':
        return 'from-blue-400/20 to-blue-600/20 border-blue-400/30';
      case 'counterpoint':
        return 'from-orange-400/20 to-orange-600/20 border-orange-400/30';
      case 'connection':
        return 'from-green-400/20 to-green-600/20 border-green-400/30';
      case 'practical-tip':
        return 'from-purple-400/20 to-purple-600/20 border-purple-400/30';
      case 'deep-dive':
        return 'from-indigo-400/20 to-indigo-600/20 border-indigo-400/30';
      case 'historical-context':
        return 'from-amber-400/20 to-amber-600/20 border-amber-400/30';
      case 'future-implications':
        return 'from-cyan-400/20 to-cyan-600/20 border-cyan-400/30';
      default:
        return 'from-yellow-400/20 to-yellow-600/20 border-yellow-400/30';
    }
  };

  if (!isVisible) return null;

  return (
    <div
      ref={panelRef}
      className="fixed z-50 bg-slate-900/95 backdrop-blur-lg border border-slate-700 rounded-xl shadow-2xl transition-all duration-300 flex flex-col"
      style={{
        left: panelPosition.x,
        top: panelPosition.y,
        width: isMinimized ? '300px' : '420px',
        height: isMinimized ? '60px' : '600px',
        cursor: isDragging ? 'grabbing' : 'default',
        maxHeight: '80vh'
      }}
    >
      {/* Header */}
      <div 
        className="drag-handle flex items-center justify-between p-4 border-b border-slate-700 cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
      >
        <div className="flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-yellow-400 animate-pulse" />
          <h3 className="font-semibold text-white">AI Insights</h3>
          <span className="text-xs bg-yellow-400/20 text-yellow-400 px-2 py-1 rounded">+5 pts</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-1 text-slate-400 hover:text-white transition-colors"
            title={isMinimized ? 'Maximize' : 'Minimize'}
          >
            {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
          </button>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-red-400 transition-colors"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      {!isMinimized && (
        <div className="flex-1 overflow-hidden flex flex-col">
          {!isOnline ? (
            <div className="flex-1 flex items-center justify-center text-center text-slate-400 p-4">
              <div>
                <div className="w-12 h-12 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-3">
                  <Lightbulb className="w-6 h-6" />
                </div>
                <p className="text-sm">Insights unavailable offline</p>
                <p className="text-xs mt-1">Connect to internet for AI-powered insights</p>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-slate-600 scrollbar-track-slate-800">
              {insights.length === 0 ? (
                <div className="text-center text-slate-400 py-8">
                  <div className="animate-spin w-8 h-8 border-4 border-yellow-400 border-t-transparent rounded-full mx-auto mb-3"></div>
                  <p className="text-sm">Generating insights...</p>
                  <p className="text-xs mt-1">AI is analyzing the content</p>
                </div>
              ) : (
                <>
                  <div className="text-center mb-4">
                    <div className="inline-flex items-center gap-2 bg-slate-800/50 px-3 py-1 rounded-full">
                      <span className="text-xs text-slate-400">
                        {insights.length} insight{insights.length !== 1 ? 's' : ''} found
                      </span>
                      <div className="w-1 h-1 bg-yellow-400 rounded-full animate-pulse"></div>
                    </div>
                  </div>
                  <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
                    {insights.map((insight) => (
                      <div key={insight.id} className="group relative">
                        <div className={`absolute -inset-0.5 bg-gradient-to-r ${getInsightColor(insight.type)} rounded-lg blur opacity-20 group-hover:opacity-40 transition-opacity duration-200`}></div>
                        <div className={`relative bg-slate-800/50 rounded-lg p-3 border ${getInsightColor(insight.type).split(' ')[2]}`}>
                          <div className="flex items-start gap-2 mb-2">
                            <div className="p-1.5 bg-slate-700 rounded-lg flex-shrink-0">
                              {getInsightIcon(insight.type)}
                            </div>
                            <div className="flex-1 min-w-0">
                              <h4 className="font-medium text-white text-sm mb-1 break-words">
                                {insight.title}
                              </h4>
                              <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                                  insight.type === 'key-takeaway' ? 'bg-yellow-400' :
                                  insight.type === 'did-you-know' ? 'bg-blue-400' :
                                  insight.type === 'practical-tip' ? 'bg-purple-400' :
                                  insight.type === 'counterpoint' ? 'bg-orange-400' : 'bg-green-400'
                                }`} />
                                <span className="text-xs text-slate-400 capitalize">
                                  {insight.type.replace('-', ' ')}
                                </span>
                              </div>
                            </div>
                          </div>

                          <p className="text-sm text-slate-300 leading-relaxed break-words">
                            {insight.content}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Footer */}
          <div className="p-3 border-t border-slate-700">
            <div className="text-xs text-slate-400 text-center">
              <span className="bg-gradient-to-r from-yellow-400/10 to-orange-400/10 border border-yellow-400/20 px-2 py-1 rounded">
                🧠 Powered by Gemini AI
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FloatingInsightsPanel;
