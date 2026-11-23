import React, { useState, useEffect } from 'react';
import { PDFDocument } from '../context/PDFContext';
import SimplePDFViewer from './SimplePDFViewer';
import { Loader2 } from 'lucide-react';

interface SmartPDFViewerProps {
  document: PDFDocument;
  onPageChange: (page: number) => void;
  onTextSelection?: (text: string, page: number) => void;
  onAskLLM?: (text: string, page: number) => void;
  onOpenInsights?: () => void;
  onOpenPodcast?: () => void;
  initialPage?: number;
}

const SmartPDFViewer: React.FC<SmartPDFViewerProps> = ({
  document,
  onPageChange,
  onTextSelection,
  onAskLLM,
  initialPage,
}) => {
  const [viewerMode, setViewerMode] = useState<'ready' | 'loading'>('loading');

  useEffect(() => {
    setViewerMode('ready');
  }, []);

  if (viewerMode === 'loading') {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-app-canvas text-ink-secondary">
        <Loader2 className="h-5 w-5 animate-spin text-ink-muted" strokeWidth={1.5} />
        <p className="mt-phi-3 text-phi-sm font-medium text-ink-primary">Preparing PDF viewer</p>
      </div>
    );
  }

  return (
    <div className="h-full">
      <SimplePDFViewer
        document={document}
        onPageChange={onPageChange}
        onTextSelection={onTextSelection}
        onAskLLM={onAskLLM}
        initialPage={initialPage}
      />
    </div>
  );
};

export default SmartPDFViewer;
