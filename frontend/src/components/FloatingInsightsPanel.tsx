import React from 'react';
import {
  AlertTriangle,
  Clock,
  Info,
  Key,
  Lightbulb,
  Link2,
  Loader2,
  RefreshCw,
  Search,
  Target,
  TrendingUp,
  X,
} from 'lucide-react';
import { usePDF } from '../context/usePDF';

interface FloatingInsightsPanelProps {
  isVisible: boolean;
  onClose: () => void;
  currentPage?: number;
  variant?: 'docked' | 'floating';
  hideHeader?: boolean;
}

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

const FloatingInsightsPanel: React.FC<FloatingInsightsPanelProps> = ({
  isVisible,
  onClose,
  currentPage = 1,
  hideHeader = false,
}) => {
  const {
    insights,
    isLoadingInsights,
    insightsError,
    isOnline,
    currentDocument,
    getInsights,
  } = usePDF();

  if (!isVisible) return null;

  const handleRefresh = () => {
    if (currentDocument) {
      getInsights(currentDocument.id, currentPage, true);
    }
  };

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-app-surface">
      {!hideHeader && (
        <div className="flex h-phi-bar shrink-0 items-center justify-between border-b border-[rgba(25,24,22,0.08)] bg-paper-50 px-phi-4">
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
              onClick={handleRefresh}
              disabled={!isOnline || isLoadingInsights}
              className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary disabled:opacity-40"
              title="Refresh insights"
              aria-label="Refresh insights"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${isLoadingInsights ? 'animate-spin' : ''}`}
                strokeWidth={1.5}
              />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
              title="Close insights"
              aria-label="Close insights"
            >
              <X className="h-4 w-4" strokeWidth={1.5} />
            </button>
          </div>
        </div>
      )}

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
          <div className="min-h-0 flex-1 space-y-phi-3 overflow-y-auto p-phi-3 scrollbar-thin">
            {isLoadingInsights ? (
              <div className="flex flex-col items-center justify-center py-phi-6 text-center">
                <Loader2 className="h-5 w-5 animate-spin text-accent" strokeWidth={1.5} />
                <p className="mt-phi-3 text-phi-sm font-medium text-ink-primary">
                  Generating insights
                </p>
                <p className="mt-phi-1 text-phi-xs text-ink-muted">
                  Reviewing page {currentPage}
                </p>
              </div>
            ) : insightsError ? (
              <div className="rounded-phi-md border border-semantic-negative/25 bg-semantic-negativeBg p-phi-4 text-center">
                <AlertTriangle className="mx-auto h-5 w-5 text-semantic-negative" strokeWidth={1.5} />
                <p className="mt-phi-2 text-phi-sm font-medium text-semantic-negative">
                  Could not load insights
                </p>
                <p className="mt-phi-1 text-phi-xs text-ink-secondary">{insightsError}</p>
                <button
                  type="button"
                  onClick={handleRefresh}
                  className="btn-secondary mt-phi-4 h-phi-ctrl-sm text-phi-xs"
                >
                  Try again
                </button>
              </div>
            ) : insights.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-phi-6 text-center">
                <Lightbulb className="h-5 w-5 text-ink-faint" strokeWidth={1.5} />
                <p className="mt-phi-3 text-phi-sm font-medium text-ink-primary">
                  No insights extracted yet
                </p>
                <p className="mt-phi-1 text-phi-xs text-ink-muted">
                  Run analysis for page {currentPage}.
                </p>
                <button
                  type="button"
                  onClick={handleRefresh}
                  className="btn-secondary mt-phi-4 h-phi-ctrl-sm text-phi-xs"
                >
                  Generate insights
                </button>
              </div>
            ) : (
              <>
                <p className="px-phi-1 font-mono text-phi-2xs tabular-nums text-ink-muted">
                  {insights.length} note{insights.length !== 1 ? 's' : ''} extracted
                </p>
                <div className="space-y-phi-2">
                  {insights.map((insight) => (
                    <article
                      key={insight.id}
                      className="folio-mark rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-paper-50 py-phi-3 pl-phi-4 pr-phi-3"
                    >
                      <div className="flex items-start justify-between gap-phi-2">
                        <h4 className="text-phi-xs font-medium leading-phi-snug text-ink-primary">
                          {insight.title}
                        </h4>
                        <span className="mt-0.5 shrink-0">{getInsightIcon(insight.type)}</span>
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
    </div>
  );
};

export default FloatingInsightsPanel;
