import React, { useState, useEffect, useRef } from 'react';
import {
  Lightbulb,
  AlertTriangle,
  Link2,
  X,
  Minimize2,
  Maximize2,
  Target,
  Search,
  Clock,
  TrendingUp,
  Key,
  Info,
  Loader2,
} from 'lucide-react';
import { usePDF } from '../context/usePDF';

interface FloatingInsightsPanelProps {
  isVisible: boolean;
  onClose: () => void;
  position?: { x: number; y: number };
  currentPage?: number;
}

const FloatingInsightsPanel: React.FC<FloatingInsightsPanelProps> = ({
  isVisible,
  onClose,
  position = { x: 110, y: 78 },
  currentPage = 1,
}) => {
  const { insights, isOnline, currentDocument, getInsights } = usePDF();
  const [isMinimized, setIsMinimized] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [panelPosition, setPanelPosition] = useState(position);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isVisible && currentDocument && insights.length === 0) {
      getInsights(currentDocument.id, currentPage);
    }
  }, [currentDocument, currentPage, getInsights, insights.length, isVisible]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget || (e.target as HTMLElement).classList.contains('drag-handle')) {
      setIsDragging(true);
      const rect = panelRef.current?.getBoundingClientRect();
      if (rect) {
        setDragOffset({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top,
        });
      }
    }
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        setPanelPosition({
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y,
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
    const cls = 'h-4 w-4 text-ink-muted';
    switch (type) {
      case 'key-takeaway':
        return <Key className={cls} strokeWidth={1.5} />;
      case 'did-you-know':
        return <Info className={cls} strokeWidth={1.5} />;
      case 'counterpoint':
        return <AlertTriangle className={cls} strokeWidth={1.5} />;
      case 'connection':
        return <Link2 className={cls} strokeWidth={1.5} />;
      case 'practical-tip':
        return <Target className={cls} strokeWidth={1.5} />;
      case 'deep-dive':
        return <Search className={cls} strokeWidth={1.5} />;
      case 'historical-context':
        return <Clock className={cls} strokeWidth={1.5} />;
      case 'future-implications':
        return <TrendingUp className={cls} strokeWidth={1.5} />;
      default:
        return <Lightbulb className={cls} strokeWidth={1.5} />;
    }
  };

  if (!isVisible) return null;

  return (
    <div
      ref={panelRef}
      className="fixed z-50 flex flex-col overflow-hidden rounded-phi-lg border border-[rgba(25,24,22,0.14)] bg-app-surface shadow-float"
      style={{
        left: panelPosition.x,
        top: panelPosition.y,
        width: isMinimized ? '287px' : '365px',
        height: isMinimized ? '53px' : '591px',
        cursor: isDragging ? 'grabbing' : 'default',
        maxHeight: '82vh',
      }}
    >
      {/* Drag Header */}
      <div
        className="drag-handle flex h-phi-bar shrink-0 cursor-grab items-center justify-between border-b border-[rgba(25,24,22,0.08)] bg-paper-50 px-phi-4 active:cursor-grabbing"
        onMouseDown={handleMouseDown}
      >
        <div className="flex items-center gap-phi-2">
          <Lightbulb className="h-4 w-4 text-accent" strokeWidth={1.5} />
          <h3 className="text-phi-sm font-medium text-ink-primary">Page insights</h3>
          <span className="font-mono text-phi-2xs tabular-nums text-ink-muted">
            p. {currentPage}
          </span>
        </div>
        <div className="flex items-center gap-phi-1">
          <button
            type="button"
            onClick={() => setIsMinimized((prev) => !prev)}
            className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
            title={isMinimized ? 'Expand' : 'Minimize'}
            aria-label={isMinimized ? 'Expand insights' : 'Minimize insights'}
          >
            {isMinimized ? (
              <Maximize2 className="h-3.5 w-3.5" strokeWidth={1.5} />
            ) : (
              <Minimize2 className="h-3.5 w-3.5" strokeWidth={1.5} />
            )}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
            title="Close"
            aria-label="Close insights"
          >
            <X className="h-4 w-4" strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {/* Content */}
      {!isMinimized && (
        <div className="flex min-h-0 flex-1 flex-col">
          {!isOnline ? (
            <div className="flex flex-1 flex-col items-center justify-center p-phi-5 text-center">
              <Lightbulb className="h-5 w-5 text-ink-faint" strokeWidth={1.5} />
              <p className="mt-phi-3 text-phi-sm font-medium text-ink-primary">
                Insights unavailable offline
              </p>
              <p className="mt-phi-1 text-phi-xs text-ink-muted">
                Reconnect to analyze the current page.
              </p>
            </div>
          ) : (
            <div className="flex-1 space-y-phi-3 overflow-y-auto p-phi-4 scrollbar-thin">
              {insights.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-phi-6 text-center">
                  <Loader2 className="h-5 w-5 animate-spin text-ink-muted" strokeWidth={1.5} />
                  <p className="mt-phi-3 text-phi-sm font-medium text-ink-primary">
                    Generating insights
                  </p>
                  <p className="mt-phi-1 text-phi-xs text-ink-muted">
                    Reviewing page {currentPage}
                  </p>
                </div>
              ) : (
                <>
                  <p className="font-mono text-phi-2xs tabular-nums text-ink-muted">
                    {insights.length} note{insights.length !== 1 ? 's' : ''} extracted
                  </p>
                  <div className="space-y-phi-3">
                    {insights.map((insight) => (
                      <article
                        key={insight.id}
                        className="folio-mark rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-paper-50 py-phi-3 pl-phi-4 pr-phi-3"
                      >
                        <div className="flex items-start justify-between gap-phi-2">
                          <h4 className="text-phi-sm font-medium leading-phi-snug text-ink-primary">
                            {insight.title}
                          </h4>
                          <span className="mt-phi-1 shrink-0">{getInsightIcon(insight.type)}</span>
                        </div>
                        <p className="mt-phi-1 font-mono text-phi-2xs capitalize text-ink-muted">
                          {insight.type.replace(/-/g, ' ')}
                        </p>
                        <p className="mt-phi-2 text-phi-xs leading-phi text-ink-secondary">
                          {insight.content}
                        </p>
                      </article>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FloatingInsightsPanel;
