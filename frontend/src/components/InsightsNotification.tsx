import React, { useEffect } from 'react';
import { Lightbulb, X } from 'lucide-react';

interface InsightsNotificationProps {
  isVisible: boolean;
  onOpenInsights: () => void;
  onDismiss: () => void;
  insightCount?: number;
}

const InsightsNotification: React.FC<InsightsNotificationProps> = ({
  isVisible,
  onOpenInsights,
  onDismiss,
  insightCount = 0,
}) => {
  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => {
        onDismiss();
      }, 8000);
      return () => clearTimeout(timer);
    }
  }, [isVisible, onDismiss]);

  if (!isVisible) return null;

  return (
    <div className="fixed right-phi-5 top-phi-7 z-40 w-phi-sidebar max-w-[calc(100vw-2rem)]">
      <div className="folio-mark rounded-phi-md border border-[rgba(25,24,22,0.12)] bg-app-surface py-phi-3 pl-phi-4 pr-phi-3 shadow-float">
        <div className="flex items-start gap-phi-3">
          <Lightbulb className="mt-phi-1 h-4 w-4 shrink-0 text-accent" strokeWidth={1.5} />
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-phi-2">
              <h4 className="text-phi-sm font-medium text-ink-primary">Page insights ready</h4>
              <button
                type="button"
                onClick={onDismiss}
                className="rounded-phi-xs p-phi-1 text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
                aria-label="Dismiss notification"
              >
                <X className="h-3.5 w-3.5" strokeWidth={1.5} />
              </button>
            </div>
            <p className="mt-phi-1 text-phi-xs leading-phi text-ink-secondary">
              {insightCount > 0
                ? `${insightCount} note${insightCount === 1 ? '' : 's'} extracted for the open page.`
                : 'Notes have been extracted for the open page.'}
            </p>
            <div className="mt-phi-3">
              <button
                type="button"
                onClick={onOpenInsights}
                className="btn-secondary h-phi-ctrl-sm px-phi-3 text-phi-xs"
              >
                View insights
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InsightsNotification;
