import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { WS_URL } from '../config';
import {
  ArrowUpDown,
  Check,
  CheckSquare,
  ChevronDown,
  FileText,
  FolderPlus,
  Gauge,
  GitMerge,
  Loader2,
  LogOut,
  MessageSquare,
  RefreshCw,
  Search,
  Settings,
  Trash2,
  X,
} from 'lucide-react';
import { usePDF } from '../context/usePDF';
import DocumentCard from '../components/DocumentCard';
import UploadZone from '../components/UploadZone';
import AIPersonaJobForm from '../components/AIPersonaJobForm';
import SimpleChatbot from '../components/SimpleChatbot';
import BrandMark from '../components/BrandMark';
import { PDFValidationResult } from '../utils/pdfValidator';
import { mergeDocuments, splitDocument } from '../lib/api';
import { buildSplitRanges } from '../lib/splitRanges';
import { normalizeUploadSocketMessage, type UploadProgressState } from '../lib/uploadProgress';

type FileWithValidation = File & {
  validationResult?: PDFValidationResult;
};

interface MergeResult {
  merged_document?: {
    source_documents?: number;
    name?: string;
  };
}

interface SplitResult {
  original_document?: {
    name?: string;
  };
  split_documents?: unknown[];
}

const getErrorMessage = (error: unknown, fallback = 'Unexpected error') =>
  error instanceof Error ? error.message : fallback;

const getStoredPageCount = (metadata: unknown, fallback = 10): number => {
  if (!metadata || typeof metadata !== 'object') {
    return fallback;
  }

  const pageCount =
    (metadata as { page_count?: unknown; pageCount?: unknown }).page_count ??
    (metadata as { pageCount?: unknown }).pageCount;
  if (typeof pageCount === 'number' && Number.isFinite(pageCount) && pageCount > 0) {
    return pageCount;
  }
  if (typeof pageCount === 'string') {
    const parsed = Number(pageCount);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
  }

  return fallback;
};

const safeGetTime = (dateField: Date | string | null | undefined): number => {
  try {
    if (!dateField) return 0;
    const date = dateField instanceof Date ? dateField : new Date(dateField);
    return Number.isNaN(date.getTime()) ? 0 : date.getTime();
  } catch {
    return 0;
  }
};

const formatTotalSize = (bytes: number): string => {
  if (bytes <= 0) return '0 KB';
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const SORT_LABELS: Record<'recentlyOpened' | 'recentlyUploaded' | 'nameAZ' | 'size', string> = {
  recentlyUploaded: 'Recently uploaded',
  recentlyOpened: 'Recently opened',
  nameAZ: 'Name (A–Z)',
  size: 'Largest first',
};

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const {
    documents,
    uploadDocument,
    uploadBulkDocuments,
    updateDocuments,
    fetchAllDocuments,
    loadDocument,
    deleteDocument,
    deleteAllDocuments,
    renameDocument,
    isLoadingDocuments,
  } = usePDF();
  const { user, loading: authLoading, signOut: signOutUser } = useAuth();

  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login');
    }
  }, [authLoading, navigate, user]);

  const handleSignOut = useCallback(async () => {
    try {
      await signOutUser();
      navigate('/');
    } catch (error) {
      console.error('Failed to sign out:', error);
    }
  }, [navigate, signOutUser]);

  const [showBulkUpload, setShowBulkUpload] = useState(false);
  const [showPersonaForm, setShowPersonaForm] = useState(false);
  const [pendingBulkUpload, setPendingBulkUpload] = useState<{
    files: File[];
    considerPrevious: boolean;
  } | null>(null);
  const [currentPersona, setCurrentPersona] = useState<string>('');
  const [currentJob, setCurrentJob] = useState<string>('');
  const [showChatbot, setShowChatbot] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const [clientId, setClientId] = useState<string>('');
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [uploadProgress, setUploadProgress] = useState<UploadProgressState>({});

  useEffect(() => {
    const savedPersona = localStorage.getItem('lastPersona');
    const savedJob = localStorage.getItem('lastJob');
    if (savedPersona) setCurrentPersona(savedPersona);
    if (savedJob) setCurrentJob(savedJob);
    localStorage.removeItem('documents');
  }, []);

  useEffect(() => {
    if (authLoading) return;

    const storedId = localStorage.getItem('currentClientId');
    const resolvedId = user?.id || storedId || crypto.randomUUID();

    setClientId(resolvedId);
    localStorage.setItem('currentClientId', resolvedId);
  }, [authLoading, user]);

  useEffect(() => {
    if (!clientId) return;
    fetchAllDocuments();
  }, [clientId, fetchAllDocuments]);

  useEffect(() => {
    if (!clientId) return;

    let ws: WebSocket | null = null;
    let isComponentMounted = true;

    const clearUploadProgress = (jobId: string) => {
      setUploadProgress((previousProgress) => {
        if (!(jobId in previousProgress)) return previousProgress;
        const nextProgress = { ...previousProgress };
        delete nextProgress[jobId];
        return nextProgress;
      });
    };

    const connectWebSocket = () => {
      if (!isComponentMounted) return;

      try {
        const BACKEND_WS_URL = WS_URL;
        setWsStatus('connecting');
        ws = new WebSocket(`${BACKEND_WS_URL}/ws/${clientId}`);

        ws.onopen = () => {
          if (!isComponentMounted) return;
          setWsStatus('connected');
        };

        ws.onmessage = (event) => {
          if (!isComponentMounted) return;

          try {
            const message = JSON.parse(event.data);
            const uploadMessage = normalizeUploadSocketMessage(message);

            if (uploadMessage) {
              const { type, jobId, progress } = uploadMessage;

              if (jobId) {
                setUploadProgress((previousProgress) => ({
                  ...previousProgress,
                  [jobId]: progress,
                }));
              }

              if (type === 'complete' || type === 'processing_complete') {
                window.setTimeout(() => {
                  if (!isComponentMounted) return;
                  if (jobId) clearUploadProgress(jobId);
                  fetchAllDocuments();
                }, 1000);
              }

              if (type === 'error' && jobId) {
                window.setTimeout(() => {
                  if (!isComponentMounted) return;
                  clearUploadProgress(jobId);
                }, 5000);
              }

              return;
            }
          } catch (parseError) {
            console.warn('Failed to parse WebSocket message:', parseError);
          }
        };

        ws.onerror = () => setWsStatus('error');
        ws.onclose = () => setWsStatus('disconnected');
      } catch {
        setWsStatus('error');
      }
    };

    const initialTimeout = setTimeout(connectWebSocket, 1000);

    return () => {
      isComponentMounted = false;
      if (initialTimeout) clearTimeout(initialTimeout);
      if (ws) {
        ws.close(1000, 'Component unmounting');
        ws = null;
      }
    };
  }, [clientId, fetchAllDocuments]);

  const handleSingleUpload = async (files: File | File[]) => {
    if (files instanceof File) {
      const fileWithValidation = files as FileWithValidation;
      if (fileWithValidation.validationResult && !fileWithValidation.validationResult.isValid) {
        const proceed = window.confirm(
          `PDF validation issues detected:\n\n${fileWithValidation.validationResult.issues.join('\n')}\n\nProceed anyway?`
        );
        if (!proceed) return;
      }

      try {
        const jobId = await uploadDocument(
          files,
          clientId,
          currentPersona || 'General Reader',
          currentJob || 'Reading and understanding'
        );
        navigate(`/reader/${jobId}`);
      } catch (error) {
        console.error('Single upload error:', error);
        alert('Upload failed. Please try again.');
      }
    }
  };

  const handleMultipleUpload = async (files: File | File[], considerPrevious: boolean = false) => {
    if (Array.isArray(files)) {
      const filesWithValidation = files as FileWithValidation[];
      const invalidFiles = filesWithValidation.filter(
        (f) => f.validationResult && !f.validationResult.isValid
      );

      if (invalidFiles.length > 0) {
        const invalidNames = invalidFiles.map((f) => f.name).join('\n');
        const proceed = window.confirm(
          `${invalidFiles.length} file(s) have validation issues:\n\n${invalidNames}\n\nProceed with the valid files only?`
        );
        if (!proceed) return;
        files = files.filter((f) => {
          const validation = (f as FileWithValidation).validationResult;
          return !validation || validation.isValid;
        });
      }

      if (files.length === 0) {
        alert('No valid files to upload.');
        return;
      }

      if (!currentPersona || !currentJob) {
        setPendingBulkUpload({ files, considerPrevious });
        setShowPersonaForm(true);
        return;
      }

      await runBulkUpload(files, considerPrevious, currentPersona, currentJob);
    }
  };

  const runBulkUpload = async (
    files: File[],
    considerPrevious: boolean,
    persona: string,
    job: string
  ) => {
    try {
      const result = await uploadBulkDocuments(
        files,
        clientId,
        persona,
        job,
        considerPrevious
      );
      const failedCount = result.files.filter(
        (file) => file.status === 'failed' || file.status === 'error' || file.error
      ).length;
      setShowBulkUpload(false);
      alert(
        failedCount > 0
          ? `Added ${result.documents.length} document(s) to your library. ${failedCount} file(s) failed.`
          : `Uploaded ${result.documents.length} document(s) to your library.`
      );
    } catch (error) {
      console.error('Bulk upload error:', error);
      alert('Upload failed. Please try again.');
    }
  };

  const handlePersonaJobSubmit = async (persona: string, job: string) => {
    setCurrentPersona(persona);
    setCurrentJob(job);
    setShowPersonaForm(false);
    localStorage.setItem('lastPersona', persona);
    localStorage.setItem('lastJob', job);
    if (pendingBulkUpload) {
      const queued = pendingBulkUpload;
      setPendingBulkUpload(null);
      await runBulkUpload(queued.files, queued.considerPrevious, persona, job);
    }
  };

  const openDocument = async (documentId: string) => {
    const docExists = documents.some((doc) => doc.id === documentId);
    if (docExists) {
      try {
        await loadDocument(documentId);
      } catch (error) {
        console.warn('Failed to track document open in backend:', error);
      }

      updateDocuments(
        documents.map((doc) => (doc.id === documentId ? { ...doc, lastOpened: new Date() } : doc))
      );
    }
    navigate(`/reader/${documentId}`);
  };

  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const [showMergeDialog, setShowMergeDialog] = useState(false);
  const [mergeFileName, setMergeFileName] = useState('');
  const [isMerging, setIsMerging] = useState(false);
  const [showSplitDialog, setShowSplitDialog] = useState(false);
  const [splitDocumentId, setSplitDocumentId] = useState<string>('');
  const [splitDocumentName, setSplitDocumentName] = useState<string>('');
  const [splitDocumentPages, setSplitDocumentPages] = useState<number>(0);
  const [numSplits, setNumSplits] = useState<number>(2);
  const [splitRanges, setSplitRanges] = useState<Array<{ name: string; startPage: number; endPage: number }>>([]);
  const [isSplitting, setIsSplitting] = useState(false);
  const [sortType, setSortType] = useState<'recentlyOpened' | 'recentlyUploaded' | 'nameAZ' | 'size'>('recentlyUploaded');
  const [showSortMenu, setShowSortMenu] = useState(false);
  const sortMenuRef = useRef<HTMLDivElement | null>(null);

  const toggleSelect = (id: string) => {
    setSelectedDocuments((prev) =>
      prev.includes(id) ? prev.filter((docId) => docId !== id) : [...prev, id]
    );
  };

  const clearDocuments = async () => {
    try {
      const confirmed = window.confirm(
        `Delete all ${documents.length} document(s) from your library? This cannot be undone.`
      );
      if (!confirmed) return;

      await deleteAllDocuments(false);
      setSelectedDocuments([]);
      setIsSelectMode(false);
    } catch (error) {
      console.error('Failed to clear all documents:', error);
      alert('Failed to delete all documents. Please try again.');
    }
  };

  const handleMergeDocuments = async () => {
    if (selectedDocuments.length < 2) {
      setIsSelectMode(true);
      alert('Select at least 2 documents to merge.');
      return;
    }
    setShowMergeDialog(true);
  };

  const executeMerge = async () => {
    if (selectedDocuments.length < 2) {
      alert('Select at least 2 documents to merge.');
      return;
    }

    setIsMerging(true);
    try {
      const result = (await mergeDocuments(selectedDocuments, mergeFileName.trim())) as MergeResult;
      alert(
        `Merged ${result.merged_document?.source_documents || selectedDocuments.length} documents into "${
          result.merged_document?.name || mergeFileName || 'merged PDF'
        }".`
      );
      setSelectedDocuments([]);
      setIsSelectMode(false);
      setShowMergeDialog(false);
      setMergeFileName('');
      await fetchAllDocuments();
    } catch (error) {
      console.error('Failed to merge documents:', error);
      alert(`Failed to merge documents: ${getErrorMessage(error)}`);
    } finally {
      setIsMerging(false);
    }
  };

  const cancelMerge = () => {
    setShowMergeDialog(false);
    setMergeFileName('');
  };

  const updateNumSplits = (newNumSplits: number) => {
    const maxSplits = Math.min(10, Math.max(2, splitDocumentPages));
    const clamped = Math.min(maxSplits, Math.max(2, newNumSplits));
    setNumSplits(clamped);
    setSplitRanges(
      buildSplitRanges(
        splitDocumentPages,
        clamped,
        splitRanges.map((range) => range.name)
      )
    );
  };

  const updateSplitRange = (
    index: number,
    field: 'name' | 'startPage' | 'endPage',
    value: string | number
  ) => {
    setSplitRanges((prev) =>
      prev.map((range, i) => (i === index ? { ...range, [field]: value } : range))
    );
  };

  const validateSplitRanges = (): string | null => {
    const usedPages = new Set<number>();

    for (let i = 0; i < splitRanges.length; i++) {
      const range = splitRanges[i];
      if (range.startPage < 1 || range.endPage > splitDocumentPages || range.startPage > range.endPage) {
        return `Invalid page range for split ${i + 1}: ${range.startPage}-${range.endPage}. Document has ${splitDocumentPages} pages.`;
      }

      for (let page = range.startPage; page <= range.endPage; page++) {
        if (usedPages.has(page)) {
          return `Page overlap detected: page ${page} is used in multiple splits.`;
        }
        usedPages.add(page);
      }
    }

    return null;
  };

  const executeSplit = async () => {
    const validationError = validateSplitRanges();
    if (validationError) {
      alert(validationError);
      return;
    }

    setIsSplitting(true);
    try {
      const splits = splitRanges.map((range, index) => ({
        name: range.name.trim() || `${splitDocumentName.replace('.pdf', '')}_part_${index + 1}`,
        start_page: range.startPage,
        end_page: range.endPage,
      }));

      const result = (await splitDocument(splitDocumentId, splits)) as SplitResult;
      alert(
        `Split "${result.original_document?.name || splitDocumentName}" into ${
          result.split_documents?.length || splits.length
        } documents.`
      );
      cancelSplit();
      await fetchAllDocuments();
    } catch (error) {
      console.error('Failed to split document:', error);
      alert(`Failed to split document: ${getErrorMessage(error)}`);
    } finally {
      setIsSplitting(false);
    }
  };

  const cancelSplit = () => {
    setShowSplitDialog(false);
    setSplitDocumentId('');
    setSplitDocumentName('');
    setSplitDocumentPages(0);
    setNumSplits(2);
    setSplitRanges([]);
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showSortMenu && sortMenuRef.current && !sortMenuRef.current.contains(event.target as Node)) {
        setShowSortMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showSortMenu]);

  const sortedDocuments = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    const filtered = query
      ? documents.filter((doc) => (doc.name || '').toLowerCase().includes(query))
      : documents;

    return [...filtered].sort((a, b) => {
      switch (sortType) {
        case 'recentlyOpened': {
          const aLastOpened = safeGetTime(a.lastOpened);
          const bLastOpened = safeGetTime(b.lastOpened);
          if (aLastOpened === 0 && bLastOpened === 0) {
            return (
              (safeGetTime(b.lastUploaded) || safeGetTime(b.uploadDate)) -
              (safeGetTime(a.lastUploaded) || safeGetTime(a.uploadDate))
            );
          }
          if (aLastOpened === 0) return 1;
          if (bLastOpened === 0) return -1;
          return bLastOpened - aLastOpened;
        }
        case 'recentlyUploaded':
          return (
            (safeGetTime(b.lastUploaded) || safeGetTime(b.uploadDate)) -
            (safeGetTime(a.lastUploaded) || safeGetTime(a.uploadDate))
          );
        case 'nameAZ':
          return (a.name || '').toLowerCase().trim().localeCompare((b.name || '').toLowerCase().trim());
        case 'size':
          return (b.size || 0) - (a.size || 0);
        default:
          return 0;
      }
    });
  }, [documents, searchQuery, sortType]);

  const totalBytes = useMemo(
    () => documents.reduce((sum, doc) => sum + (doc.size || 0), 0),
    [documents]
  );

  const handleOpen = (id: string) => {
    openDocument(id);
  };

  const handleSplit = async (id: string) => {
    const document = documents.find((doc) => doc.id === id);
    if (!document) return;

    let pageCount = getStoredPageCount(document.metadata);
    try {
      const loadedDocument = await loadDocument(id);
      pageCount = getStoredPageCount(loadedDocument?.metadata || document.metadata);
    } catch {
      // Fall back to existing metadata count if network fetch fails
    }

    if (pageCount < 2) {
      alert(`"${document.name}" only has 1 page and cannot be split.`);
      return;
    }

    setSplitDocumentId(id);
    setSplitDocumentName(document.name);
    setSplitDocumentPages(pageCount);
    setNumSplits(2);
    setSplitRanges(buildSplitRanges(pageCount, 2));
    setShowSplitDialog(true);
  };

  const handleDelete = async (id: string) => {
    const document = documents.find((doc) => doc.id === id);
    if (!document) return;

    const confirmed = window.confirm(`Delete "${document.name}"? This cannot be undone.`);
    if (confirmed) {
      try {
        await deleteDocument(id);
      } catch (error) {
        console.error('Failed to delete document:', error);
        alert('Failed to delete document. Please try again.');
      }
    }
  };

  const handleRename = async (id: string) => {
    const document = documents.find((doc) => doc.id === id);
    if (!document) return;

    const newName = prompt(`Rename "${document.name}" to:`, document.name);
    if (newName && newName.trim() && newName.trim() !== document.name) {
      try {
        await renameDocument(id, newName.trim());
      } catch (error) {
        console.error('Failed to rename document:', error);
        alert('Failed to rename document. Please try again.');
      }
    }
  };

  const handleSelectMode = () => {
    setIsSelectMode(true);
  };

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-app-bg text-phi-sm text-ink-secondary">
        Loading workspace
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-app-bg text-ink-primary">
      {/* Top Application Bar */}
      <header className="sticky top-0 z-30 border-b border-[rgba(25,24,22,0.09)] bg-app-surface">
        <div className="mx-auto flex h-phi-bar w-full max-w-phi-shell items-center justify-between gap-phi-4 px-phi-4 sm:px-phi-5">
          <div className="flex items-center gap-phi-5">
            <Link
              to="/"
              className="rounded-phi-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <BrandMark />
            </Link>

            <nav className="hidden items-center gap-phi-1 md:flex">
              <span className="rounded-phi-sm bg-app-raised px-phi-3 py-phi-1 text-phi-sm font-medium text-ink-primary">
                Library
              </span>
              <Link
                to="/evals"
                className="rounded-phi-sm px-phi-3 py-phi-1 text-phi-sm text-ink-secondary transition-colors duration-phi-fast hover:bg-app-raised hover:text-ink-primary"
              >
                RAG evals
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-phi-3">
            <div
              className="hidden items-center gap-phi-2 text-phi-xs text-ink-muted sm:flex"
              title={`Index status: ${wsStatus}`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  wsStatus === 'connected'
                    ? 'bg-semantic-positive'
                    : wsStatus === 'connecting'
                      ? 'bg-semantic-warning'
                      : wsStatus === 'error'
                        ? 'bg-semantic-negative'
                        : 'bg-ink-faint'
                }`}
              />
              <span className="font-mono text-phi-2xs">
                {wsStatus === 'connected'
                  ? 'Live'
                  : wsStatus === 'connecting'
                    ? 'Connecting'
                    : wsStatus === 'error'
                      ? 'Disconnected'
                      : 'Offline'}
              </span>
            </div>

            {user && (
              <>
                <span className="hidden h-phi-4 w-px bg-[rgba(25,24,22,0.1)] sm:inline-block" />
                <span className="hidden max-w-[12rem] truncate text-phi-xs text-ink-secondary md:inline">
                  {user.email}
                </span>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="btn-ghost h-phi-ctrl-sm px-phi-3 text-phi-xs"
                >
                  <LogOut className="h-3.5 w-3.5" strokeWidth={1.5} />
                  Sign out
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main App Shell: Golden Sidebar + Fluid Content */}
      <div className="mx-auto flex w-full max-w-phi-shell flex-1 flex-col lg:flex-row">
        {/* Left Sidebar */}
        <aside className="w-full shrink-0 border-b border-[rgba(25,24,22,0.09)] bg-paper-50 p-phi-4 lg:w-phi-sidebar lg:border-b-0 lg:border-r lg:p-phi-5">
          {/* Search */}
          <div className="flex h-phi-ctrl-sm items-center gap-phi-2 rounded-phi-md border border-[rgba(25,24,22,0.12)] bg-app-surface px-phi-3 text-phi-sm focus-within:border-ink-primary focus-within:ring-2 focus-within:ring-accent/15">
            <Search className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search"
              aria-label="Search documents"
              className="w-full bg-transparent text-phi-sm text-ink-primary placeholder:text-ink-faint focus:outline-none"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="text-ink-muted hover:text-ink-primary"
                aria-label="Clear search"
              >
                <X className="h-3.5 w-3.5" strokeWidth={1.5} />
              </button>
            )}
          </div>

          {/* Workspace Navigation & Actions */}
          <div className="mt-phi-5">
            <p className="px-phi-2 text-phi-xs text-ink-muted">Workspace</p>
            <div className="mt-phi-2 space-y-phi-1">
              <button
                type="button"
                onClick={() => setShowBulkUpload((prev) => !prev)}
                className={`flex h-phi-ctrl-sm w-full items-center gap-phi-2 rounded-phi-md px-phi-3 text-phi-sm transition-colors duration-phi-fast ${
                  showBulkUpload
                    ? 'bg-app-raised font-medium text-ink-primary'
                    : 'text-ink-secondary hover:bg-app-raised/70 hover:text-ink-primary'
                }`}
              >
                <FolderPlus className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
                <span className="truncate">Bulk upload</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  if (isSelectMode) {
                    setIsSelectMode(false);
                    setSelectedDocuments([]);
                  } else {
                    setIsSelectMode(true);
                  }
                }}
                className={`flex h-phi-ctrl-sm w-full items-center gap-phi-2 rounded-phi-md px-phi-3 text-phi-sm transition-colors duration-phi-fast ${
                  isSelectMode
                    ? 'bg-app-raised font-medium text-ink-primary'
                    : 'text-ink-secondary hover:bg-app-raised/70 hover:text-ink-primary'
                }`}
              >
                <CheckSquare className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
                <span className="truncate">{isSelectMode ? 'Exit selection' : 'Select files'}</span>
              </button>

              <button
                type="button"
                onClick={handleMergeDocuments}
                className="flex h-phi-ctrl-sm w-full items-center gap-phi-2 rounded-phi-md px-phi-3 text-phi-sm text-ink-secondary transition-colors duration-phi-fast hover:bg-app-raised/70 hover:text-ink-primary"
              >
                <GitMerge className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
                <span className="truncate">Merge PDFs</span>
              </button>

              <button
                type="button"
                onClick={() => setShowChatbot((prev) => !prev)}
                className={`flex h-phi-ctrl-sm w-full items-center gap-phi-2 rounded-phi-md px-phi-3 text-phi-sm transition-colors duration-phi-fast ${
                  showChatbot
                    ? 'bg-app-raised font-medium text-ink-primary'
                    : 'text-ink-secondary hover:bg-app-raised/70 hover:text-ink-primary'
                }`}
              >
                <MessageSquare className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
                <span className="truncate">Library chat</span>
              </button>

              <Link
                to="/evals"
                className="flex h-phi-ctrl-sm w-full items-center gap-phi-2 rounded-phi-md px-phi-3 text-phi-sm text-ink-secondary transition-colors duration-phi-fast hover:bg-app-raised/70 hover:text-ink-primary"
              >
                <Gauge className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
                <span className="truncate">RAG evals</span>
              </Link>
            </div>
          </div>

          {/* Reading Profile Section */}
          <div className="mt-phi-5 border-t border-[rgba(25,24,22,0.08)] pt-phi-5">
            <div className="flex items-center justify-between px-phi-2">
              <p className="text-phi-xs text-ink-muted">Reading profile</p>
              <button
                type="button"
                onClick={() => setShowPersonaForm(true)}
                className="rounded-phi-xs p-phi-1 text-ink-muted transition-colors duration-phi-fast hover:bg-app-raised hover:text-ink-primary"
                title="Edit reading profile"
                aria-label="Edit reading profile"
              >
                <Settings className="h-3.5 w-3.5" strokeWidth={1.5} />
              </button>
            </div>

            {currentPersona || currentJob ? (
              <div className="folio-mark mt-phi-2 rounded-phi-md border border-[rgba(25,24,22,0.08)] bg-app-surface py-phi-3 pl-phi-4 pr-phi-3">
                {currentPersona && (
                  <p className="text-phi-xs font-medium text-ink-primary">{currentPersona}</p>
                )}
                {currentJob && (
                  <p className="mt-phi-1 text-phi-xs leading-phi text-ink-secondary">{currentJob}</p>
                )}
              </div>
            ) : (
              <div className="mt-phi-2 rounded-phi-md border border-[rgba(25,24,22,0.08)] bg-app-surface p-phi-3">
                <p className="text-phi-xs leading-phi text-ink-secondary">
                  Set your role and reading goal to tailor cross-document links.
                </p>
                <button
                  type="button"
                  onClick={() => setShowPersonaForm(true)}
                  className="btn-secondary mt-phi-3 h-phi-ctrl-sm w-full text-phi-xs"
                >
                  Configure profile
                </button>
              </div>
            )}
          </div>

          {/* Library Maintenance */}
          {documents.length > 0 && (
            <div className="mt-phi-5 border-t border-[rgba(25,24,22,0.08)] pt-phi-4">
              <button
                type="button"
                onClick={clearDocuments}
                className="flex h-phi-ctrl-sm w-full items-center gap-phi-2 rounded-phi-md px-phi-3 text-phi-sm text-semantic-negative transition-colors duration-phi-fast hover:bg-semantic-negativeBg"
              >
                <Trash2 className="h-4 w-4 shrink-0" strokeWidth={1.5} />
                <span>Clear library</span>
              </button>
            </div>
          )}
        </aside>

        {/* Main Fluid Content */}
        <main className="min-w-0 flex-1 px-phi-4 py-phi-5 sm:px-phi-6 sm:py-phi-6">
          {/* Page Header */}
          <div className="flex flex-wrap items-end justify-between gap-phi-4">
            <div>
              <h1 className="font-serif text-phi-xl font-normal leading-phi-tight tracking-[-0.02em] text-ink-primary">
                Document library
              </h1>
              <p className="mt-phi-1 font-mono text-phi-xs tabular-nums text-ink-muted">
                {documents.length} file{documents.length !== 1 ? 's' : ''} · {formatTotalSize(totalBytes)}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-phi-2">
              <div ref={sortMenuRef} className="relative">
                <button
                  type="button"
                  onClick={() => setShowSortMenu((prev) => !prev)}
                  className="btn-secondary h-phi-ctrl-sm gap-phi-2 px-phi-3 text-phi-xs"
                >
                  <ArrowUpDown className="h-3.5 w-3.5 text-ink-muted" strokeWidth={1.5} />
                  <span>{SORT_LABELS[sortType]}</span>
                  <ChevronDown className="h-3.5 w-3.5 text-ink-muted" strokeWidth={1.5} />
                </button>

                {showSortMenu && (
                  <div className="absolute right-0 z-20 mt-phi-1 w-48 rounded-phi-md border border-[rgba(25,24,22,0.12)] bg-app-surface py-phi-1 shadow-float">
                    {(Object.keys(SORT_LABELS) as Array<keyof typeof SORT_LABELS>).map((key) => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => {
                          setSortType(key);
                          setShowSortMenu(false);
                        }}
                        className={`flex w-full items-center justify-between px-phi-3 py-phi-2 text-left text-phi-sm transition-colors duration-phi-fast hover:bg-paper-200/70 ${
                          sortType === key ? 'font-medium text-ink-primary' : 'text-ink-secondary'
                        }`}
                      >
                        <span>{SORT_LABELS[key]}</span>
                        {sortType === key && (
                          <Check className="h-4 w-4 text-accent" strokeWidth={1.5} />
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={() => fetchAllDocuments()}
                disabled={isLoadingDocuments}
                className="btn-secondary h-phi-ctrl-sm w-phi-ctrl-sm p-0"
                title="Refresh library"
                aria-label="Refresh library"
              >
                <RefreshCw
                  className={`h-4 w-4 shrink-0 text-ink-secondary ${isLoadingDocuments ? 'animate-spin' : ''}`}
                  strokeWidth={1.5}
                />
              </button>

              <button
                type="button"
                onClick={() => setShowBulkUpload((prev) => !prev)}
                className="btn-primary h-phi-ctrl-sm px-phi-4 text-phi-xs"
              >
                <FolderPlus className="h-3.5 w-3.5" strokeWidth={1.5} />
                {showBulkUpload ? 'Close bulk upload' : 'Bulk upload'}
              </button>
            </div>
          </div>

          {/* Single-PDF Quick Drop Strip */}
          <div className="mt-phi-5">
            <UploadZone onFileSelect={handleSingleUpload} multiple={false} compact />

            {/* Live Upload Progress Indicators */}
            {Object.entries(uploadProgress).length > 0 && (
              <div className="mt-phi-3 space-y-phi-2">
                {Object.entries(uploadProgress).map(([jobId, progress]) => (
                  <div
                    key={jobId}
                    className="rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-app-surface px-phi-4 py-phi-3 shadow-subtle"
                  >
                    <div className="flex items-center justify-between gap-phi-2 text-phi-xs">
                      <span className="font-medium text-ink-primary">
                        {progress.status === 'error'
                          ? 'Processing failed'
                          : progress.status === 'complete'
                            ? 'Processing complete'
                            : 'Indexing document'}
                      </span>
                      <span className="font-mono tabular-nums text-accent-ink">
                        {progress.percent}%
                      </span>
                    </div>
                    <div className="mt-phi-2 h-1.5 w-full overflow-hidden rounded-full bg-paper-200">
                      <div
                        className={`h-full rounded-full transition-[width] duration-phi ${
                          progress.status === 'error'
                            ? 'bg-semantic-negative'
                            : progress.status === 'complete'
                              ? 'bg-semantic-positive'
                              : 'bg-accent'
                        }`}
                        style={{ width: `${progress.percent}%` }}
                      />
                    </div>
                    {progress.message && (
                      <p className="mt-phi-2 text-phi-xs text-ink-muted">{progress.message}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Expandable Bulk Upload Panel */}
          {showBulkUpload && (
            <section className="mt-phi-4 rounded-phi-lg border border-[rgba(25,24,22,0.1)] bg-app-surface p-phi-5 shadow-subtle">
              <div className="mb-phi-4 flex items-center justify-between gap-phi-3">
                <div>
                  <h2 className="text-phi-sm font-medium text-ink-primary">Bulk upload</h2>
                  <p className="mt-phi-1 text-phi-xs text-ink-muted">
                    Upload multiple PDFs together to build cross-document links
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowBulkUpload(false)}
                  className="rounded-phi-sm p-phi-1 text-ink-muted hover:bg-paper-200 hover:text-ink-primary"
                  aria-label="Close bulk upload"
                >
                  <X className="h-4 w-4" strokeWidth={1.5} />
                </button>
              </div>
              <UploadZone onFileSelect={handleMultipleUpload} multiple />
            </section>
          )}

          {/* Document Grid */}
          <section className="mt-phi-5">
            {isLoadingDocuments ? (
              <div className="flex flex-col items-center justify-center rounded-phi-lg border border-[rgba(25,24,22,0.09)] bg-app-surface py-phi-7 text-center">
                <Loader2 className="h-5 w-5 animate-spin text-ink-muted" strokeWidth={1.5} />
                <p className="mt-phi-3 text-phi-sm font-medium text-ink-primary">Loading library</p>
                <p className="mt-phi-1 text-phi-xs text-ink-muted">
                  Fetching documents from your workspace
                </p>
              </div>
            ) : documents.length === 0 ? (
              <div className="flex flex-col items-center justify-center rounded-phi-lg border border-[rgba(25,24,22,0.09)] bg-app-surface px-phi-5 py-phi-7 text-center">
                <span className="flex h-phi-6 w-phi-6 items-center justify-center rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-paper-100 text-ink-muted">
                  <FileText className="h-5 w-5" strokeWidth={1.5} />
                </span>
                <p className="mt-phi-4 text-phi-sm font-medium text-ink-primary">No documents yet</p>
                <p className="mt-phi-1 max-w-phi-modal-sm text-phi-xs leading-phi text-ink-muted">
                  Drop a PDF in the upload strip above to open the reader immediately, or use bulk upload to index a folder of files.
                </p>
              </div>
            ) : sortedDocuments.length === 0 ? (
              <div className="rounded-phi-lg border border-[rgba(25,24,22,0.09)] bg-app-surface px-phi-5 py-phi-6 text-center">
                <p className="text-phi-sm font-medium text-ink-primary">
                  No documents match “{searchQuery}”
                </p>
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="mt-phi-2 text-phi-xs font-medium text-accent-ink hover:underline"
                >
                  Clear search filter
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-phi-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                {sortedDocuments.map((doc) => (
                  <DocumentCard
                    key={doc.id}
                    document={doc}
                    onClick={() => (isSelectMode ? toggleSelect(doc.id) : openDocument(doc.id))}
                    isSelectMode={isSelectMode}
                    isSelected={selectedDocuments.includes(doc.id)}
                    onOpen={handleOpen}
                    onSplit={handleSplit}
                    onDelete={handleDelete}
                    onRename={handleRename}
                    onSelectMode={handleSelectMode}
                  />
                ))}
              </div>
            )}
          </section>
        </main>
      </div>

      {/* Floating Selection Action Bar */}
      {isSelectMode && selectedDocuments.length > 0 && (
        <div className="fixed bottom-phi-5 left-1/2 z-40 -translate-x-1/2 rounded-phi-lg border border-[rgba(25,24,22,0.14)] bg-ink-primary px-phi-4 py-phi-2 text-paper-50 shadow-float">
          <div className="flex items-center gap-phi-4">
            <span className="font-mono text-phi-xs tabular-nums">
              {selectedDocuments.length} selected
            </span>

            {selectedDocuments.length >= 2 && (
              <button
                type="button"
                onClick={handleMergeDocuments}
                className="btn-accent h-phi-ctrl-sm px-phi-3 text-phi-xs"
              >
                <GitMerge className="h-3.5 w-3.5" strokeWidth={1.5} />
                Merge PDFs
              </button>
            )}

            <button
              type="button"
              onClick={() => {
                setSelectedDocuments([]);
                setIsSelectMode(false);
              }}
              className="rounded-phi-sm px-phi-3 py-phi-1 text-phi-xs text-paper-300 transition-colors duration-phi-fast hover:bg-white/10 hover:text-white"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Merge Dialog */}
      {showMergeDialog && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Merge documents"
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink-primary/35 p-phi-4 backdrop-blur-[2px]"
        >
          <div className="w-full max-w-phi-modal-sm rounded-phi-lg border border-[rgba(25,24,22,0.12)] bg-app-surface p-phi-5 shadow-float">
            <h3 className="font-serif text-phi-lg font-normal text-ink-primary">Merge documents</h3>
            <p className="mt-phi-1 text-phi-sm text-ink-secondary">
              Combine {selectedDocuments.length} selected files into a single PDF.
            </p>

            <div className="mt-phi-5">
              <label className="text-phi-sm font-medium text-ink-primary" htmlFor="merge-filename">
                Output filename <span className="font-normal text-ink-muted">(optional)</span>
              </label>
              <input
                id="merge-filename"
                type="text"
                value={mergeFileName}
                onChange={(e) => setMergeFileName(e.target.value)}
                placeholder="merged_briefing"
                className="mt-phi-2 h-phi-ctrl w-full rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-paper-50 px-phi-3 text-phi-sm text-ink-primary placeholder:text-ink-faint focus:border-ink-primary focus:outline-none focus:ring-2 focus:ring-accent/15"
              />
              <p className="mt-phi-2 text-phi-xs text-ink-muted">
                Leave blank to generate a sequential name automatically.
              </p>
            </div>

            <div className="mt-phi-6 flex items-center justify-end gap-phi-3">
              <button
                type="button"
                onClick={cancelMerge}
                disabled={isMerging}
                className="btn-secondary h-phi-ctrl"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={executeMerge}
                disabled={isMerging}
                className="btn-primary h-phi-ctrl"
              >
                {isMerging ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
                    Merging
                  </>
                ) : (
                  'Merge files'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Split Dialog */}
      {showSplitDialog && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Split document"
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink-primary/35 p-phi-4 backdrop-blur-[2px]"
        >
          <div className="max-h-[90vh] w-full max-w-phi-modal-lg overflow-y-auto rounded-phi-lg border border-[rgba(25,24,22,0.12)] bg-app-surface p-phi-5 shadow-float">
            <h3 className="font-serif text-phi-lg font-normal text-ink-primary">Split document</h3>
            <p className="mt-phi-1 text-phi-sm text-ink-secondary">
              Splitting “{splitDocumentName}” (
              <span className="font-mono tabular-nums">{splitDocumentPages}</span> pages) into separate files.
            </p>

            <div className="mt-phi-5">
              <label className="text-phi-sm font-medium text-ink-primary" htmlFor="num-splits">
                Number of parts
              </label>
              <input
                id="num-splits"
                type="number"
                min={2}
                max={Math.min(10, Math.max(2, splitDocumentPages))}
                value={numSplits}
                onChange={(e) => updateNumSplits(parseInt(e.target.value, 10) || 2)}
                className="mt-phi-2 block h-phi-ctrl w-phi-8 rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-paper-50 px-phi-3 font-mono text-phi-sm tabular-nums text-ink-primary focus:border-ink-primary focus:outline-none focus:ring-2 focus:ring-accent/15"
              />
            </div>

            <div className="mt-phi-5 space-y-phi-3">
              {splitRanges.map((range, index) => {
                const rangePages = Math.max(0, range.endPage - range.startPage + 1);
                return (
                <div
                  key={index}
                  className="rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-paper-50 p-phi-4"
                >
                  <div className="mb-phi-3 flex items-center justify-between">
                    <span className="text-phi-sm font-medium text-ink-primary">Part {index + 1}</span>
                    <span className="font-mono text-phi-xs tabular-nums text-ink-muted">
                      pp. {range.startPage}–{range.endPage} ({rangePages}{' '}
                      {rangePages === 1 ? 'page' : 'pages'})
                    </span>
                  </div>
                  <div className="grid gap-phi-3 sm:grid-cols-3">
                    <div>
                      <label className="block text-phi-xs text-ink-muted">Name (optional)</label>
                      <input
                        type="text"
                        value={range.name}
                        onChange={(e) => updateSplitRange(index, 'name', e.target.value)}
                        placeholder={`part_${index + 1}`}
                        className="mt-phi-1 h-phi-ctrl-sm w-full rounded-phi-sm border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 text-phi-sm text-ink-primary placeholder:text-ink-faint focus:border-ink-primary focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-phi-xs text-ink-muted">Start page</label>
                      <input
                        type="number"
                        min={1}
                        max={splitDocumentPages}
                        value={range.startPage}
                        onChange={(e) =>
                          updateSplitRange(index, 'startPage', parseInt(e.target.value, 10) || 1)
                        }
                        className="mt-phi-1 h-phi-ctrl-sm w-full rounded-phi-sm border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 font-mono text-phi-sm tabular-nums text-ink-primary focus:border-ink-primary focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-phi-xs text-ink-muted">End page</label>
                      <input
                        type="number"
                        min={1}
                        max={splitDocumentPages}
                        value={range.endPage}
                        onChange={(e) =>
                          updateSplitRange(index, 'endPage', parseInt(e.target.value, 10) || 1)
                        }
                        className="mt-phi-1 h-phi-ctrl-sm w-full rounded-phi-sm border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 font-mono text-phi-sm tabular-nums text-ink-primary focus:border-ink-primary focus:outline-none"
                      />
                    </div>
                  </div>
                </div>
                );
              })}
            </div>

            <div className="mt-phi-6 flex items-center justify-end gap-phi-3">
              <button
                type="button"
                onClick={cancelSplit}
                disabled={isSplitting}
                className="btn-secondary h-phi-ctrl"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={executeSplit}
                disabled={isSplitting}
                className="btn-primary h-phi-ctrl"
              >
                {isSplitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
                    Splitting
                  </>
                ) : (
                  'Split PDF'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reading Profile Modal */}
      <AIPersonaJobForm
        isVisible={showPersonaForm}
        onSubmit={handlePersonaJobSubmit}
        onCancel={() => {
          setPendingBulkUpload(null);
          setShowPersonaForm(false);
        }}
        initialPersona={currentPersona}
        initialJob={currentJob}
      />

      {/* Library Chat */}
      <SimpleChatbot
        documentContext={undefined}
        isMinimized={!showChatbot}
        onToggleMinimize={() => setShowChatbot((prev) => !prev)}
        viewType="library"
      />
    </div>
  );
};

export default HomePage;
