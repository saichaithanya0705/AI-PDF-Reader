import React, { useState, useEffect } from 'react';
import { PDFDocument } from '../context/PDFContext';
import SimplePDFViewer from './SimplePDFViewer';
import { RefreshCw } from 'lucide-react';

interface SmartPDFViewerProps {
  document: PDFDocument;
  onPageChange: (page: number) => void;
  onTextSelection?: (text: string, page: number) => void;
  onAskLLM?: (text: string, page: number) => void;
  onOpenInsights?: () => void;
  onOpenPodcast?: () => void;
}

const SmartPDFViewer: React.FC<SmartPDFViewerProps> = ({
  document,
  onPageChange,
  onTextSelection,
  onAskLLM,
  onOpenInsights,
  onOpenPodcast
}) => {
  const [viewerMode, setViewerMode] = useState<'ready' | 'loading'>('loading');

  // Use SimplePDFViewer (react-pdf)
  useEffect(() => {
    console.log('📚 Initializing React-PDF viewer');
    setViewerMode('ready');
  }, []);

  // Reset viewer when document changes
  useEffect(() => {
    console.log('📄 Document changed:', document.name);
  }, [document.id]);

  if (viewerMode === 'loading') {
    return (
      <div className="flex flex-col h-full bg-slate-900 text-white">
        <div className="flex items-center justify-center flex-1">
          <div className="text-center">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-400" />
            <div className="text-lg font-medium mb-2">Loading PDF Viewer</div>
            <div className="text-sm text-slate-400">Initializing PDF display...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full">
      {/* React-PDF Viewer */}
      <SimplePDFViewer
        document={document}
        onPageChange={onPageChange}
        onTextSelection={onTextSelection}
        onAskLLM={onAskLLM}
      />
    </div>
  );
};

export default SmartPDFViewer;
