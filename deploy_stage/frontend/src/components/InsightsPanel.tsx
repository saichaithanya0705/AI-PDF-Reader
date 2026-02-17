import React from 'react';
import { Lightbulb, Brain, AlertTriangle, Link } from 'lucide-react';
import { usePDF } from '../context/PDFContext';

const InsightsPanel: React.FC = () => {
  const { insights, isOnline } = usePDF();

  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'key-insight':
        return <Brain className="w-4 h-4 text-cyan-400" />;
      case 'did-you-know':
        return <Lightbulb className="w-4 h-4 text-yellow-400" />;
      case 'counterpoint':
        return <AlertTriangle className="w-4 h-4 text-orange-400" />;
      case 'connection':
        return <Link className="w-4 h-4 text-purple-400" />;
      default:
        return <Lightbulb className="w-4 h-4 text-cyan-400" />;
    }
  };

  const getInsightColor = (type: string) => {
    switch (type) {
      case 'key-insight':
        return 'from-cyan-400/20 to-cyan-600/20 border-cyan-400/30';
      case 'did-you-know':
        return 'from-yellow-400/20 to-yellow-600/20 border-yellow-400/30';
      case 'counterpoint':
        return 'from-orange-400/20 to-orange-600/20 border-orange-400/30';
      case 'connection':
        return 'from-purple-400/20 to-purple-600/20 border-purple-400/30';
      default:
        return 'from-cyan-400/20 to-cyan-600/20 border-cyan-400/30';
    }
  };

  if (!isOnline) {
    return (
      <div className="h-full flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb className="w-5 h-5 text-slate-400" />
            <h3 className="font-semibold text-white">AI Insights</h3>
          </div>
          <p className="text-xs text-slate-400">Requires internet connection</p>
        </div>
        <div className="flex-1 flex items-center justify-center text-center text-slate-400 p-4">
          <div>
            <div className="w-12 h-12 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-3">
              <Lightbulb className="w-6 h-6" />
            </div>
            <p className="text-sm">Insights unavailable offline</p>
            <p className="text-xs mt-1">Connect to internet for AI-powered insights</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center gap-2 mb-2">
          <Lightbulb className="w-5 h-5 text-yellow-400 animate-pulse" />
          <h3 className="font-semibold text-white">AI Insights</h3>
        </div>
        <p className="text-xs text-slate-400">
          GPT-4o powered contextual intelligence
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {insights.length === 0 ? (
          <div className="text-center text-slate-400 py-8">
            <div className="animate-spin w-8 h-8 border-4 border-yellow-400 border-t-transparent rounded-full mx-auto mb-3"></div>
            <p className="text-sm">Generating insights...</p>
            <p className="text-xs mt-1">AI is analyzing the content</p>
          </div>
        ) : (
          insights.map((insight) => (
            <div
              key={insight.id}
              className="group relative"
            >
              <div className={`absolute -inset-0.5 bg-gradient-to-r ${getInsightColor(insight.type)} rounded-lg blur opacity-20 group-hover:opacity-40 transition-opacity duration-200`}></div>
              <div className={`relative bg-slate-800/50 rounded-lg p-4 border ${getInsightColor(insight.type).split(' ')[2]}`}>
                <div className="flex items-start gap-3 mb-3">
                  <div className="p-2 bg-slate-700 rounded-lg">
                    {getInsightIcon(insight.type)}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-medium text-white text-sm mb-1">
                      {insight.title}
                    </h4>
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${
                        insight.relevance > 0.9 ? 'bg-green-400' :
                        insight.relevance > 0.8 ? 'bg-yellow-400' : 'bg-orange-400'
                      }`} />
                      <span className="text-xs text-slate-400">
                        {Math.round(insight.relevance * 100)}% relevant
                      </span>
                    </div>
                  </div>
                </div>
                
                <p className="text-sm text-slate-300 leading-relaxed">
                  {insight.content}
                </p>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="p-4 border-t border-slate-700">
        <div className="text-xs text-slate-400 text-center">
          <span className="bg-gradient-to-r from-yellow-400/10 to-orange-400/10 border border-yellow-400/20 px-2 py-1 rounded">
            🧠 Powered by GPT-4o
          </span>
        </div>
      </div>
    </div>
  );
};

export default InsightsPanel;