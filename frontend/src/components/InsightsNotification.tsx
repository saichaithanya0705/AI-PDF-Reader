import React, { useState, useEffect } from 'react';
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
  insightCount = 0
}) => {
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    if (isVisible) {
      setIsAnimating(true);
      // Auto-dismiss after 8 seconds
      const timer = setTimeout(() => {
        onDismiss();
      }, 8000);
      return () => clearTimeout(timer);
    }
  }, [isVisible, onDismiss]);

  if (!isVisible) return null;

  return (
    <div className="fixed top-20 right-6 z-40 animate-in slide-in-from-right duration-300">
      <div className="bg-gradient-to-r from-yellow-400/90 to-orange-500/90 backdrop-blur-lg text-white rounded-xl shadow-2xl border border-yellow-400/30 p-4 max-w-sm">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-white/20 rounded-lg">
            <Lightbulb className="w-5 h-5 animate-pulse" />
          </div>
          <div className="flex-1">
            <h4 className="font-semibold text-sm mb-1">
              AI Insights Ready! 🧠
            </h4>
            <p className="text-xs text-white/90 mb-3">
              {insightCount > 0 
                ? `${insightCount} insights generated for this page. Click to explore!`
                : 'AI has analyzed this page and found interesting insights.'
              }
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={onOpenInsights}
                className="bg-white/20 hover:bg-white/30 text-white text-xs px-3 py-1.5 rounded-lg transition-colors font-medium"
              >
                View Insights (+5 pts)
              </button>
              <button
                onClick={onDismiss}
                className="text-white/70 hover:text-white transition-colors"
                title="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
        
        {/* Progress bar for auto-dismiss */}
        <div className="mt-3 h-1 bg-white/20 rounded-full overflow-hidden">
          <div 
            className="h-full bg-white/40 rounded-full transition-all duration-[8000ms] ease-linear"
            style={{ width: isAnimating ? '0%' : '100%' }}
          />
        </div>
      </div>
    </div>
  );
};

export default InsightsNotification;
