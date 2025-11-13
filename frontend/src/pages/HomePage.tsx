import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { API_URL, WS_URL } from '../config';
import {
  Upload,
  FileText,
  Zap,
  Brain,
  Sparkles,
  Plus,
  FolderOpen,
  Clock,
  Settings,
  Pointer,
  GitMerge,
  ListFilter,
  FolderPlus,
  Trash2,
  LogOut,
  UserCircle,
  Home,
} from 'lucide-react';
import { usePDF } from '../context/PDFContext';
import DocumentCard from '../components/DocumentCard';
import UploadZone from '../components/UploadZone';
import PersonaJobForm from '../components/PersonaJobForm';
import AIPersonaJobForm from '../components/AIPersonaJobForm';
import SimpleChatbot from '../components/SimpleChatbot';
import { formatDistanceToNow } from 'date-fns';
import { PDFValidator, PDFValidationResult } from '../utils/pdfValidator';

const HomePage: React.FC = () => {
  console.log('🏠 HomePage component rendering...');

  const navigate = useNavigate();
  const {
    documents,
    uploadDocument,
    uploadBulkDocuments,
    updateDocuments,
    fetchAllDocuments,
    deleteDocument,
    deleteAllDocuments,
    renameDocument,
    isLoadingDocuments
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
      console.error('❌ Failed to sign out:', error);
    }
  }, [navigate, signOutUser]);

  console.log('📊 HomePage state:', {
    documentsCount: documents?.length || 0,
    isLoadingDocuments
  });
  const [showBulkUpload, setShowBulkUpload] = useState(false);
  const [showPersonaForm, setShowPersonaForm] = useState(false);
  const [currentPersona, setCurrentPersona] = useState<string>('');
  const [currentJob, setCurrentJob] = useState<string>('');
  const [showChatbot, setShowChatbot] = useState(false);

  const [clientId, setClientId] = useState<string>('');
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [uploadProgress, setUploadProgress] = useState<{[key: string]: {percent: number, message: string}}>({});

  // Generate clientId on mount and load saved persona/job
  useEffect(() => {
    // Load saved persona and job
    const savedPersona = localStorage.getItem('lastPersona');
    const savedJob = localStorage.getItem('lastJob');
    if (savedPersona) setCurrentPersona(savedPersona);
    if (savedJob) setCurrentJob(savedJob);

    // Clear potentially corrupted localStorage data if needed
    try {
      const stored = localStorage.getItem('documents');
      if (stored) {
        JSON.parse(stored); // Test if it's valid JSON
      }
    } catch (error) {
      console.warn('⚠️ Corrupted documents in localStorage, clearing...', error);
      localStorage.removeItem('documents');
    }
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
  }, [clientId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debug: Log current documents when they change
  useEffect(() => {
    console.log('📚 Current documents in state:', documents.length);
  }, [documents]);

  // WebSocket Connection for Real-time Updates
  useEffect(() => {
    if (!clientId) return;

    let ws: WebSocket | null = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 3;
    let reconnectTimeout: number | null = null;
    let isComponentMounted = true;

    const connectWebSocket = () => {
      if (!isComponentMounted) return;

      try {
  const BACKEND_WS_URL = WS_URL;
        console.log(`📡 Connecting WebSocket for client: ${clientId}`);
        setWsStatus('connecting');

        ws = new WebSocket(`${BACKEND_WS_URL}/ws/${clientId}`);

        ws.onopen = () => {
          if (!isComponentMounted) return;
          console.log('✅ WebSocket connected successfully');
          setWsStatus('connected');
          reconnectAttempts = 0;
        };

        ws.onmessage = (event) => {
          if (!isComponentMounted) return;

          try {
            const message = JSON.parse(event.data);
            console.log('📨 WebSocket message received:', message);

            switch (message.type) {
              case 'processing_complete':
                console.log('✅ Document processing completed:', message.data);
                setTimeout(() => fetchAllDocuments(), 1000);
                break;
              default:
                console.log('📄 WebSocket message:', message.type);
            }
          } catch (parseError) {
            console.warn('⚠️ Failed to parse WebSocket message:', parseError);
          }
        };

        ws.onerror = () => setWsStatus('error');
        ws.onclose = () => setWsStatus('disconnected');

      } catch (error) {
        console.log('⚠️ WebSocket connection failed:', error);
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
      // Check validation if available
      const fileWithValidation = files as any;
      if (fileWithValidation.validationResult) {
        const validation = fileWithValidation.validationResult as PDFValidationResult;
        console.log('📋 File validation result:', validation);

        if (!validation.isValid) {
          const proceed = window.confirm(
            `⚠️ PDF Validation Issues Detected:\n\n${validation.issues.join('\n')}\n\nDo you want to proceed anyway? The file may not work properly.`
          );
          if (!proceed) {
            console.log('❌ User cancelled upload due to validation issues');
            return;
          }
        } else if (validation.warnings.length > 0) {
          console.log('⚠️ PDF has warnings:', validation.warnings.join(', '));
        }
      }

      // Single upload: Open directly without requiring persona/job
      try {
        console.log('Starting single upload for:', files.name);
        const jobId = await uploadDocument(files, clientId, currentPersona || 'General Reader', currentJob || 'Reading and understanding');
        console.log('Upload completed, job ID:', jobId);

        // Navigate immediately - the ReaderPage will handle the loading state
        console.log('Navigating to reader for job:', jobId);
        navigate(`/reader/${jobId}`);

      } catch (error) {
        console.error('Single upload error:', error);
        alert('Upload failed. Please try again.');
      }
    }
  };

  const handleMultipleUpload = async (files: File | File[], considerPrevious: boolean = false) => {
    if (Array.isArray(files)) {
      // Check validation for all files
      const filesWithValidation = files as any[];
      const invalidFiles = filesWithValidation.filter(f =>
        f.validationResult && !f.validationResult.isValid
      );
      const warningFiles = filesWithValidation.filter(f =>
        f.validationResult && f.validationResult.isValid && f.validationResult.warnings.length > 0
      );

      if (invalidFiles.length > 0) {
        const invalidNames = invalidFiles.map(f => f.name).join('\n');
        const proceed = window.confirm(
          `⚠️ ${invalidFiles.length} file(s) have validation issues:\n\n${invalidNames}\n\nDo you want to proceed with the valid files only?`
        );
        if (!proceed) {
          console.log('❌ User cancelled bulk upload due to validation issues');
          return;
        }
        // Filter out invalid files
        files = files.filter(f => {
          const validation = (f as any).validationResult;
          return !validation || validation.isValid;
        });
      }

      if (warningFiles.length > 0) {
        console.log(`⚠️ ${warningFiles.length} files have warnings but will be uploaded`);
      }

      if (files.length === 0) {
        alert('No valid files to upload.');
        return;
      }

      // Bulk upload: Require persona/job for intelligent library building
      if (!currentPersona || !currentJob) {
        setShowPersonaForm(true);
        return;
      }

      try {
        const jobIds = await uploadBulkDocuments(files, clientId, currentPersona, currentJob, considerPrevious);
        console.log('Bulk Job IDs:', jobIds);
        setShowBulkUpload(false); // Hide upload zone after successful upload
        // Show success message
        alert(`Successfully uploaded ${files.length} valid documents to your intelligent library!`);
      } catch (error) {
        console.error('Bulk upload error:', error);
        alert('Upload failed. Please try again.');
      }
    }
  };

  const handlePersonaJobSubmit = (persona: string, job: string) => {
    setCurrentPersona(persona);
    setCurrentJob(job);
    setShowPersonaForm(false);

    // Save to localStorage
    localStorage.setItem('lastPersona', persona);
    localStorage.setItem('lastJob', job);
  };

  // Update lastOpened
  const openDocument = async (documentId: string) => {
    // Update lastOpened if document exists, but navigate regardless
    const docExists = documents.some(doc => doc.id === documentId);
    if (docExists) {
      try {
        // Track document open in backend
  await fetch(`${API_URL}/api/documents/${documentId}/open`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        console.log(`📖 Marked document as opened in backend: ${documentId}`);
      } catch (error) {
        console.warn('⚠️ Failed to track document open in backend:', error);
        // Continue anyway - don't block navigation
      }

      // Update frontend state
      updateDocuments(documents.map(doc =>
        doc.id === documentId ? { ...doc, lastOpened: new Date() } : doc
      ));
    }
    console.log('Opening document:', documentId, 'Document exists:', docExists);
    navigate(`/reader/${documentId}`);
  };

  const [showMenu, setShowMenu] = useState(false);
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
  const [splitRanges, setSplitRanges] = useState<Array<{name: string, startPage: number, endPage: number}>>([]);
  const [isSplitting, setIsSplitting] = useState(false);
  const quickActionsRef = useRef<HTMLDivElement | null>(null);

  const toggleSelect = (id: string) => {
    setSelectedDocuments(prev =>
      prev.includes(id) ? prev.filter(docId => docId !== id) : [...prev, id]
    );
  };

  const clearDocuments = async () => {
    try {
      console.log('🗑️ Clearing all documents');
      
      // Ask for confirmation
      const confirmed = window.confirm(
        `Are you sure you want to delete all documents?\n\n` +
        `This will delete ${documents.length} document(s).\n\n` +
        `This action cannot be undone.`
      );
      
      if (!confirmed) return;

      // Use the backend API to delete all documents
      await deleteAllDocuments(false); // false = soft delete
      
      // Clear select mode state
      setSelectedDocuments([]);
      setIsSelectMode(false);
      
      console.log('✅ All documents cleared successfully');
    } catch (error) {
      console.error('❌ Failed to clear all documents:', error);
      alert('Failed to delete all documents. Please try again.');
    }
  };

  const handleMergeDocuments = async () => {
    if (selectedDocuments.length < 2) {
      alert('Please select at least 2 documents to merge.');
      return;
    }

    setShowMergeDialog(true);
  };

  const executeMerge = async () => {
    if (selectedDocuments.length < 2) {
      alert('Please select at least 2 documents to merge.');
      return;
    }

    setIsMerging(true);

    try {
      console.log('🔗 Merging documents:', selectedDocuments);
      console.log('📝 Output name:', mergeFileName || '(auto-generate)');

      const response = await fetch('/api/merge-documents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_ids: selectedDocuments,
          output_name: mergeFileName.trim()
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to merge documents');
      }

      const result = await response.json();

      console.log('✅ Documents merged successfully:', result);

      // Show success message
      alert(`Successfully merged ${result.merged_document.source_documents} documents into "${result.merged_document.name}"`);

      // Reset state
      setSelectedDocuments([]);
      setIsSelectMode(false);
      setShowMergeDialog(false);
      setMergeFileName('');

      // Refresh document list to show the new merged document
      window.location.reload();

    } catch (error) {
      console.error('❌ Failed to merge documents:', error);
      alert(`Failed to merge documents: ${error.message}`);
    } finally {
      setIsMerging(false);
    }
  };

  const cancelMerge = () => {
    setShowMergeDialog(false);
    setMergeFileName('');
  };

  const updateNumSplits = (newNumSplits: number) => {
    setNumSplits(newNumSplits);

    // Update split ranges array
    const newRanges = [];
    const pagesPerSplit = Math.floor(splitDocumentPages / newNumSplits);

    for (let i = 0; i < newNumSplits; i++) {
      const startPage = i * pagesPerSplit + 1;
      const endPage = i === newNumSplits - 1 ? splitDocumentPages : (i + 1) * pagesPerSplit;

      newRanges.push({
        name: splitRanges[i]?.name || '',
        startPage: splitRanges[i]?.startPage || startPage,
        endPage: splitRanges[i]?.endPage || endPage
      });
    }

    setSplitRanges(newRanges);
  };

  const updateSplitRange = (index: number, field: 'name' | 'startPage' | 'endPage', value: string | number) => {
    const newRanges = [...splitRanges];
    newRanges[index] = { ...newRanges[index], [field]: value };
    setSplitRanges(newRanges);
  };

  const validateSplitRanges = (): string | null => {
    const usedPages = new Set<number>();

    for (let i = 0; i < splitRanges.length; i++) {
      const range = splitRanges[i];

      // Validate range
      if (range.startPage < 1 || range.endPage > splitDocumentPages || range.startPage > range.endPage) {
        return `Invalid page range for split ${i + 1}: ${range.startPage}-${range.endPage}. Document has ${splitDocumentPages} pages.`;
      }

      // Check for overlaps
      for (let page = range.startPage; page <= range.endPage; page++) {
        if (usedPages.has(page)) {
          return `Page overlap detected: page ${page} is used in multiple splits.`;
        }
        usedPages.add(page);
      }
    }

    return null; // No errors
  };

  const executeSplit = async () => {
    // Validate ranges
    const validationError = validateSplitRanges();
    if (validationError) {
      alert(validationError);
      return;
    }

    setIsSplitting(true);

    try {
      console.log('✂️ Splitting document:', splitDocumentId);
      console.log('📄 Split ranges:', splitRanges);

      const splits = splitRanges.map((range, index) => ({
        name: range.name.trim() || `${splitDocumentName.replace('.pdf', '')}_part_${index + 1}`,
        start_page: range.startPage,
        end_page: range.endPage
      }));

      const response = await fetch('/api/split-document', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_id: splitDocumentId,
          splits: splits
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to split document');
      }

      const result = await response.json();

      console.log('✅ Document split successfully:', result);

      // Show success message
      alert(`Successfully split "${result.original_document.name}" into ${result.split_documents.length} documents`);

      // Reset state
      setShowSplitDialog(false);
      setSplitDocumentId('');
      setSplitDocumentName('');
      setSplitDocumentPages(0);
      setNumSplits(2);
      setSplitRanges([]);

      // Refresh document list to show the new split documents
      window.location.reload();

    } catch (error) {
      console.error('❌ Failed to split document:', error);
      alert(`Failed to split document: ${error.message}`);
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

  const [sortType, setSortType] = useState<'recentlyOpened' | 'recentlyUploaded' | 'nameAZ' | 'size'>('recentlyUploaded');
  const [showSortMenu, setShowSortMenu] = useState(false);

  // Close sort menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showSortMenu) {
        const target = event.target as Element;
        if (!target.closest('.sort-menu-container')) {
          setShowSortMenu(false);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showSortMenu]);

  // Close quick action menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showMenu && quickActionsRef.current && !quickActionsRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showMenu]);

  // Load documents from localStorage only as fallback (database is primary)
  useEffect(() => {
    // Only load from localStorage if no documents are loaded from database
    const checkLocalStorage = setTimeout(() => {
      if (documents.length === 0 && !isLoadingDocuments) {
        const stored = localStorage.getItem('documents');
        if (stored) {
          try {
            const parsedDocs = JSON.parse(stored).map((d: any) => {
              // Safe date parsing
              let uploadDate: Date;
              let lastOpened: Date | null = null;
              let lastUploaded: Date | null = null;

              try {
                uploadDate = new Date(d.uploadDate);
                if (isNaN(uploadDate.getTime())) {
                  console.warn('Invalid upload date for document:', d.name, d.uploadDate);
                  uploadDate = new Date(); // Use current date as fallback
                }
              } catch {
                console.warn('Failed to parse upload date for document:', d.name, d.uploadDate);
                uploadDate = new Date(); // Use current date as fallback
              }

              try {
                if (d.lastOpened) {
                  lastOpened = new Date(d.lastOpened);
                  if (isNaN(lastOpened.getTime())) {
                    console.warn('Invalid last opened date for document:', d.name, d.lastOpened);
                    lastOpened = null;
                  }
                }
              } catch {
                console.warn('Failed to parse last opened date for document:', d.name, d.lastOpened);
                lastOpened = null;
              }

              try {
                if (d.lastUploaded) {
                  lastUploaded = new Date(d.lastUploaded);
                  if (isNaN(lastUploaded.getTime())) {
                    console.warn('Invalid last uploaded date for document:', d.name, d.lastUploaded);
                    lastUploaded = null;
                  }
                }
              } catch {
                console.warn('Failed to parse last uploaded date for document:', d.name, d.lastUploaded);
                lastUploaded = null;
              }

              return {
                ...d,
                uploadDate,
                lastOpened,
                lastUploaded: lastUploaded || uploadDate // Fallback to upload date
              };
            });

            console.log('📚 Loaded documents from localStorage as fallback:', parsedDocs.length);
            updateDocuments(parsedDocs);
          } catch (error) {
            console.error('❌ Error parsing documents from localStorage:', error);
            // Clear corrupted localStorage
            localStorage.removeItem('documents');
          }
        }
      }
    }, 2000); // Wait 2 seconds for database to load

    return () => clearTimeout(checkLocalStorage);
  }, [documents.length, isLoadingDocuments, updateDocuments]);

  // Save to localStorage as backup (but database is primary)
  useEffect(() => {
    if (documents.length > 0) {
      localStorage.setItem('documents', JSON.stringify(documents));
    }
  }, [documents]);

  // Helper function to safely get time from a date field
  const safeGetTime = (dateField: Date | string | null | undefined): number => {
    try {
      if (!dateField) return 0;
      
      let date: Date;
      if (dateField instanceof Date) {
        date = dateField;
      } else if (typeof dateField === 'string') {
        date = new Date(dateField);
      } else {
        return 0;
      }
      
      return isNaN(date.getTime()) ? 0 : date.getTime();
    } catch (error) {
      console.warn('Error parsing date:', dateField, error);
      return 0;
    }
  };

  // Sorted documents with comprehensive sorting logic
  const sortedDocuments = [...documents].sort((a, b) => {
    try {
      switch (sortType) {
        case 'recentlyOpened':
          // Sort by last opened time, putting never-opened documents at the end
          const aLastOpened = safeGetTime(a.lastOpened);
          const bLastOpened = safeGetTime(b.lastOpened);

          // If neither has been opened, sort by upload date
          if (aLastOpened === 0 && bLastOpened === 0) {
            const aUpload = safeGetTime(a.lastUploaded) || safeGetTime(a.uploadDate);
            const bUpload = safeGetTime(b.lastUploaded) || safeGetTime(b.uploadDate);
            return bUpload - aUpload;
          }

          // If only one has been opened, prioritize the opened one
          if (aLastOpened === 0) return 1;
          if (bLastOpened === 0) return -1;

          // Both have been opened, sort by last opened time
          return bLastOpened - aLastOpened;

        case 'recentlyUploaded':
          // Sort by most recent upload/re-upload time
          const aUploadTime = safeGetTime(a.lastUploaded) || safeGetTime(a.uploadDate);
          const bUploadTime = safeGetTime(b.lastUploaded) || safeGetTime(b.uploadDate);
          return bUploadTime - aUploadTime;

        case 'nameAZ':
          // Alphabetical sorting (case-insensitive)
          const aName = (a.name || '').toLowerCase().trim();
          const bName = (b.name || '').toLowerCase().trim();
          return aName.localeCompare(bName);

        case 'size':
          // Sort by file size (largest first)
          const aSize = a.size || 0;
          const bSize = b.size || 0;

          // If sizes are equal, sort by upload date as secondary criteria
          if (aSize === bSize) {
            const aUpload = safeGetTime(a.lastUploaded) || safeGetTime(a.uploadDate);
            const bUpload = safeGetTime(b.lastUploaded) || safeGetTime(b.uploadDate);
            return bUpload - aUpload;
          }

          return bSize - aSize;

        default:
          // Default to recently uploaded
          const defaultAUpload = safeGetTime(a.lastUploaded) || safeGetTime(a.uploadDate);
          const defaultBUpload = safeGetTime(b.lastUploaded) || safeGetTime(b.uploadDate);
          return defaultBUpload - defaultAUpload;
      }
    } catch (error) {
      console.error('Error sorting documents:', error);
      // Fallback to upload date sorting
      const fallbackA = safeGetTime(a.lastUploaded) || safeGetTime(a.uploadDate);
      const fallbackB = safeGetTime(b.lastUploaded) || safeGetTime(b.uploadDate);
      return fallbackB - fallbackA;
    }
  });

  // Debug log for sorting
  useEffect(() => {
    if (documents.length > 0) {
      console.log('📊 Current sort type:', sortType);
      console.log('📄 First 3 documents after sorting:', sortedDocuments.slice(0, 3).map(d => ({
        name: d.name,
        uploadDate: d.uploadDate,
        lastUploaded: d.lastUploaded,
        lastOpened: d.lastOpened
      })));
    }
  }, [sortType, sortedDocuments]);

  // Handle opening a document
  const handleOpen = (id: string) => {
    console.log('📖 Opening document:', id);
    openDocument(id);
  };

  // Handle splitting a document
  const handleSplit = async (id: string) => {
    console.log('✂️ Split document:', id);
    const document = documents.find(doc => doc.id === id);
    if (document) {
      // Get document page count
      try {
        const response = await fetch(`/api/documents/${id}`);
        if (response.ok) {
          const data = await response.json();
          // For now, we'll estimate pages or you can add page count to your document model
          // Let's assume we can get page count from metadata or set a default
          const pageCount = data.document.metadata?.page_count || 10; // Default fallback

          setSplitDocumentId(id);
          setSplitDocumentName(document.name);
          setSplitDocumentPages(pageCount);
          setNumSplits(2);
          setSplitRanges([
            { name: '', startPage: 1, endPage: Math.floor(pageCount / 2) },
            { name: '', startPage: Math.floor(pageCount / 2) + 1, endPage: pageCount }
          ]);
          setShowSplitDialog(true);
        }
      } catch (error) {
        console.error('Failed to get document info:', error);
        // Fallback: show dialog with default values
        setSplitDocumentId(id);
        setSplitDocumentName(document.name);
        setSplitDocumentPages(10); // Default
        setNumSplits(2);
        setSplitRanges([
          { name: '', startPage: 1, endPage: 5 },
          { name: '', startPage: 6, endPage: 10 }
        ]);
        setShowSplitDialog(true);
      }
    }
  };

  // Handle deleting a document
  const handleDelete = async (id: string) => {
    const document = documents.find(doc => doc.id === id);
    if (!document) return;

    const confirmed = window.confirm(`Are you sure you want to delete "${document.name}"?\n\nThis action cannot be undone.`);
    if (confirmed) {
      try {
        console.log('🗑️ Deleting document:', id);
        await deleteDocument(id);
        console.log('✅ Document deleted successfully');
      } catch (error) {
        console.error('❌ Failed to delete document:', error);
        alert('Failed to delete document. Please try again.');
      }
    }
  };

  // Handle renaming a document
  const handleRename = async (id: string) => {
    const document = documents.find(doc => doc.id === id);
    if (!document) return;

    const newName = prompt(`Rename document:\n\nCurrent name: ${document.name}\n\nEnter new name:`, document.name);
    if (newName && newName.trim() && newName.trim() !== document.name) {
      try {
        console.log('✏️ Renaming document:', id, 'to:', newName.trim());
        
        // Use the backend API
        await renameDocument(id, newName.trim());
        
        console.log('✅ Document renamed successfully');
      } catch (error) {
        console.error('❌ Failed to rename document:', error);
        alert('Failed to rename document. Please try again.');
      }
    }
  };

  // Handle enabling select mode
  const handleSelectMode = () => {
    console.log('✅ Enabling select mode');
    setIsSelectMode(true);
  };

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-300">
        Securing your workspace…
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 bg-slate-900/60 px-6 py-4 backdrop-blur">
        <Link to="/" className="flex items-center gap-2 text-sm text-slate-300 transition hover:text-white">
          <Home className="h-4 w-4" />
          Back to landing
        </Link>

        {user && (
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-200">
            <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1">
              <UserCircle className="h-4 w-4 text-cyan-300" />
              <span className="max-w-[12rem] truncate">{user.email}</span>
            </div>
            <button
              type="button"
              onClick={handleSignOut}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-transparent px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:border-white/30 hover:text-white"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        )}
      </div>

      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-400/10 via-purple-400/10 to-pink-400/10 animate-pulse"></div>
        <div className="relative px-6 py-16 mx-auto max-w-7xl lg:px-8">
          <div className="text-center">
            <div className="flex justify-center mb-6">
              <div className="relative">
                <div className="absolute -inset-1 bg-gradient-to-r from-cyan-400 to-purple-600 rounded-lg blur opacity-75"></div>
                <div className="relative bg-slate-900 rounded-lg p-4">
                  <Brain className="w-12 h-12 text-cyan-400" />
                </div>
              </div>
            </div>
            <div className="flex items-center justify-center gap-4 mb-4">
              <h1 className="text-5xl font-bold bg-gradient-to-r from-cyan-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                Adobe PDF Intelligence
              </h1>

              {/* WebSocket Status Indicator */}
              <div className="flex items-center gap-2 bg-slate-800/50 backdrop-blur rounded-full px-3 py-1 border border-slate-600">
                <div className={`w-2 h-2 rounded-full ${
                  wsStatus === 'connected' ? 'bg-green-400 animate-pulse' :
                  wsStatus === 'connecting' ? 'bg-yellow-400 animate-pulse' :
                  wsStatus === 'error' ? 'bg-red-400' :
                  'bg-slate-500'
                }`}></div>
                <span className="text-xs text-slate-400">
                  {wsStatus === 'connected' ? 'Live' :
                   wsStatus === 'connecting' ? 'Connecting...' :
                   wsStatus === 'error' ? 'Error' :
                   'Offline'}
                </span>
              </div>
            </div>
            <p className="text-xl text-slate-300 mb-6 max-w-3xl mx-auto">
              Experience the future of document reading with AI-powered insights, contextual recommendations,
              and intelligent connections across your entire document library.
            </p>

            {/* Current Persona/Job Display */}
            {(currentPersona || currentJob) && (
              <div className="bg-slate-800/50 rounded-lg p-4 mb-6 max-w-2xl mx-auto border border-slate-700">
                <div className="flex items-center justify-between">
                  <div className="text-left">
                    {currentPersona && (
                      <p className="text-sm text-slate-400">
                        <span className="text-cyan-400">Persona:</span> {currentPersona}
                      </p>
                    )}
                    {currentJob && (
                      <p className="text-sm text-slate-400 mt-1">
                        <span className="text-purple-400">Goal:</span> {currentJob}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => setShowPersonaForm(true)}
                    className="p-2 text-slate-400 hover:text-white transition-colors"
                    title="Edit persona and goal"
                  >
                    <Settings className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* Setup Prompt for new users */}
            {!currentPersona && !currentJob && (
              <div className="bg-gradient-to-r from-cyan-400/10 to-purple-400/10 rounded-lg p-4 mb-6 max-w-2xl mx-auto border border-cyan-400/20">
                <p className="text-slate-300 text-sm mb-3">
                  🤖 Get AI-powered personalized insights! Describe your role and goals in natural language
                </p>
                <button
                  onClick={() => setShowPersonaForm(true)}
                  className="bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-600 hover:to-purple-700 text-white text-sm font-medium py-2 px-4 rounded-lg transition-all duration-200 flex items-center gap-2"
                >
                  <Brain className="w-4 h-4" />
                  Smart Setup with AI
                </button>
              </div>
            )}
            
            {/* Feature Pills */}
            <div className="flex flex-wrap justify-center gap-4 mb-8">
              {[
                { icon: Zap, text: 'Real-time Insights' },
                { icon: Brain, text: 'AI Recommendations' },
                { icon: Sparkles, text: 'Smart Connections' },
                { icon: FileText, text: '100% Fidelity' }
              ].map(({ icon: Icon, text }) => (
                <div key={text} className="flex items-center gap-2 bg-slate-800/50 rounded-full px-4 py-2 border border-cyan-400/20">
                  <Icon className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm text-slate-300">{text}</span>
                </div>
              ))}
            </div>


          </div>
        </div>
      </div>

      {/* Upload Section */}
      <div className="px-6 py-12 mx-auto max-w-7xl lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
          {/* Single Upload */}
          <div className="relative">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-400 to-purple-600 rounded-xl blur opacity-30"></div>
            <div className="relative bg-slate-900/90 backdrop-blur rounded-xl p-8 border border-slate-700">
              <div className="text-center">
                <Plus className="w-12 h-12 text-cyan-400 mx-auto mb-4" />
                <h3 className="text-2xl font-bold text-white mb-2">Open New PDF</h3>
                <p className="text-slate-400 mb-6">Upload a fresh document to start reading with AI insights</p>
                <UploadZone
                  onFileSelect={handleSingleUpload}
                  multiple={false}
                  className="border-2 border-dashed border-cyan-400/30 hover:border-cyan-400/60 transition-colors"
                />

                {/* Progress Indicators for Single Upload */}
                {Object.entries(uploadProgress).length > 0 && (
                  <div className="mt-4 space-y-2">
                    {Object.entries(uploadProgress).map(([jobId, progress]) => (
                      <div key={jobId} className="bg-slate-800/50 rounded-lg p-3 border border-slate-600">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-white text-sm font-medium">Processing...</span>
                          <span className="text-cyan-400 text-sm">{progress.percent}%</span>
                        </div>
                        <div className="w-full bg-slate-700 rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-cyan-400 to-purple-600 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${progress.percent}%` }}
                          ></div>
                        </div>
                        <p className="text-slate-400 text-xs mt-1">{progress.message}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Bulk Upload */}
          <div className="relative">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-400 to-pink-400 rounded-xl blur opacity-30"></div>
            <div className="relative bg-slate-900/90 backdrop-blur rounded-xl p-8 border border-slate-700">
              <div className="text-center">
                <FolderOpen className="w-12 h-12 text-purple-400 mx-auto mb-4" />
                <h3 className="text-2xl font-bold text-white mb-2">Bulk Upload</h3>
                <p className="text-slate-400 mb-6">Add multiple PDFs to build your intelligent document library</p>
                <button
                  onClick={() => setShowBulkUpload(!showBulkUpload)}
                  className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white font-medium py-3 px-6 rounded-lg transition-all duration-200 flex items-center gap-2 mx-auto"
                >
                  <Upload className="w-4 h-4" />
                  {showBulkUpload ? 'Hide Upload' : 'Start Bulk Upload'}
                </button>
                {showBulkUpload && (
                  <div className="mt-6">
                    <UploadZone 
                      onFileSelect={handleMultipleUpload}
                      multiple={true}
                      className="border-2 border-dashed border-purple-400/30 hover:border-purple-400/60 transition-colors"
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Document Library */}
        <div>
          <div className="flex items-center gap-3 mb-8">
            <div className="w-8 h-8 bg-gradient-to-r from-cyan-400 to-purple-600 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-white">Your Document Library</h2>
            <div className="flex-1 h-px bg-gradient-to-r from-cyan-400/20 to-transparent"></div>
            <span className="text-sm text-slate-400 bg-slate-800 px-3 py-1 rounded-full">
              {documents.length} document{documents.length !== 1 ? 's' : ''}
            </span>
            <span className="text-xs text-slate-500 bg-slate-700 px-2 py-1 rounded-full">
              {sortType === 'recentlyUploaded' && '📤 Recently Uploaded'}
              {sortType === 'recentlyOpened' && '👁️ Recently Opened'}
              {sortType === 'nameAZ' && '🔤 A-Z'}
              {sortType === 'size' && '📊 By Size'}
            </span>

            {/* Refresh button */}
            <button
              onClick={() => {
                console.log('🔄 Refreshing document library...');
                fetchAllDocuments();
              }}
              disabled={isLoadingDocuments}
              className="p-2 text-slate-400 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Refresh library"
            >
              <svg
                className={`w-4 h-4 ${isLoadingDocuments ? 'animate-spin' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>

            {/* Three-dot menu button */}
            <div ref={quickActionsRef} className="relative">
              <button
                className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-300 transition hover:border-white/20 hover:text-white"
                onClick={() => setShowMenu(!showMenu)}
              >
                Quick actions
                <div className="flex flex-col gap-1 text-white/70">
                  <span className="h-1 w-1 rounded-full bg-current" />
                  <span className="h-1 w-1 rounded-full bg-current" />
                  <span className="h-1 w-1 rounded-full bg-current" />
                </div>
              </button>
              {showMenu && (
                <div className="absolute right-0 mt-3 w-72 overflow-hidden rounded-2xl border border-white/10 bg-slate-900/90 shadow-2xl backdrop-blur z-30">
                  <div className="border-b border-white/10 bg-white/5 px-5 py-3">
                    <p className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-400">Library actions</p>
                    <p className="mt-1 text-sm text-slate-300">Accelerate your workflow with bulk operations.</p>
                  </div>
                  <div className="flex flex-col divide-y divide-white/5">
                    <button
                      className="flex items-start gap-3 px-5 py-4 text-left text-sm text-slate-200 transition hover:bg-white/10"
                      onClick={() => {
                        setIsSelectMode(true);
                        setShowMenu(false);
                      }}
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-500/20 text-brand-100">
                        <Pointer className="h-4 w-4" />
                      </span>
                      <span className="flex flex-col gap-1">
                        <span className="font-medium text-white">Smart select mode</span>
                        <span className="text-xs text-slate-400">Enable multi-select to queue actions across documents.</span>
                      </span>
                    </button>
                    <button
                      className="flex items-start gap-3 px-5 py-4 text-left text-sm text-slate-200 transition hover:bg-white/10"
                      onClick={() => {
                        setShowMenu(false);
                        handleMergeDocuments();
                      }}
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-aurora/20 text-aurora">
                        <GitMerge className="h-4 w-4" />
                      </span>
                      <span className="flex flex-col gap-1">
                        <span className="font-medium text-white">Merge & remix</span>
                        <span className="text-xs text-slate-400">Combine selected PDFs into a curated briefing in minutes.</span>
                      </span>
                    </button>
                    <button
                      className="flex items-start gap-3 px-5 py-4 text-left text-sm text-slate-200 transition hover:bg-white/10"
                      onClick={() => {
                        setShowMenu(false);
                        setShowSortMenu(true);
                      }}
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-cyan-500/20 text-cyan-200">
                        <ListFilter className="h-4 w-4" />
                      </span>
                      <span className="flex flex-col gap-1">
                        <span className="font-medium text-white">Adaptive sorting</span>
                        <span className="text-xs text-slate-400">Reorder library by recency, usage, or file intelligence.</span>
                      </span>
                    </button>
                    <button
                      className="flex items-start gap-3 px-5 py-4 text-left text-sm text-slate-200 transition hover:bg-white/10"
                      onClick={() => {
                        setShowMenu(false);
                        setShowBulkUpload(true);
                      }}
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-500/20 text-brand-100">
                        <FolderPlus className="h-4 w-4" />
                      </span>
                      <span className="flex flex-col gap-1">
                        <span className="font-medium text-white">Bulk upload hub</span>
                        <span className="text-xs text-slate-400">Stage multiple PDFs with validation, persona tagging, and AI prep.</span>
                      </span>
                    </button>
                    <button
                      className="flex items-start gap-3 px-5 py-4 text-left text-sm text-slate-200 transition hover:bg-white/10"
                      onClick={() => {
                        setShowMenu(false);
                        setShowPersonaForm(true);
                      }}
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-purple-500/20 text-purple-200">
                        <Sparkles className="h-4 w-4" />
                      </span>
                      <span className="flex flex-col gap-1">
                        <span className="font-medium text-white">Persona preferences</span>
                        <span className="text-xs text-slate-400">Align recommendations by updating your persona & job profiles.</span>
                      </span>
                    </button>
                    <button
                      className="flex items-start gap-3 px-5 py-4 text-left text-sm text-red-200 transition hover:bg-red-500/10"
                      onClick={() => {
                        const confirmed = window.confirm('Delete every document from your library? This cannot be undone.');
                        if (confirmed) {
                          clearDocuments();
                        }
                        setShowMenu(false);
                      }}
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-red-500/20 text-red-300">
                        <Trash2 className="h-4 w-4" />
                      </span>
                      <span className="flex flex-col gap-1">
                        <span className="font-medium text-white">Delete entire library</span>
                        <span className="text-xs text-red-200/70">Permanently remove all files and reset your workspace.</span>
                      </span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Sort button */}
            <div className="relative sort-menu-container">
              <button
                className="flex items-center gap-2 px-3 py-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
                onClick={() => setShowSortMenu(!showSortMenu)}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
                </svg>
                Sort
                <svg className={`w-4 h-4 transition-transform ${showSortMenu ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showSortMenu && (
                <div className="absolute right-0 mt-2 w-56 bg-slate-800 rounded-lg shadow-xl border border-slate-700 py-2 z-20">
                  <div className="px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-700 mb-1">
                    Sort by
                  </div>

                  <button
                    onClick={() => { setSortType('recentlyUploaded'); setShowSortMenu(false); }}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-slate-700 transition-colors flex items-center gap-3 ${
                      sortType === 'recentlyUploaded' ? 'text-blue-400 bg-slate-700' : 'text-slate-300'
                    }`}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    Recently Uploaded
                    {sortType === 'recentlyUploaded' && <span className="ml-auto text-blue-400">✓</span>}
                  </button>

                  <button
                    onClick={() => { setSortType('recentlyOpened'); setShowSortMenu(false); }}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-slate-700 transition-colors flex items-center gap-3 ${
                      sortType === 'recentlyOpened' ? 'text-blue-400 bg-slate-700' : 'text-slate-300'
                    }`}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    Recently Opened
                    {sortType === 'recentlyOpened' && <span className="ml-auto text-blue-400">✓</span>}
                  </button>

                  <button
                    onClick={() => { setSortType('nameAZ'); setShowSortMenu(false); }}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-slate-700 transition-colors flex items-center gap-3 ${
                      sortType === 'nameAZ' ? 'text-blue-400 bg-slate-700' : 'text-slate-300'
                    }`}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                    Alphabetical (A-Z)
                    {sortType === 'nameAZ' && <span className="ml-auto text-blue-400">✓</span>}
                  </button>

                  <button
                    onClick={() => { setSortType('size'); setShowSortMenu(false); }}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-slate-700 transition-colors flex items-center gap-3 ${
                      sortType === 'size' ? 'text-blue-400 bg-slate-700' : 'text-slate-300'
                    }`}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                    </svg>
                    Size (Largest First)
                    {sortType === 'size' && <span className="ml-auto text-blue-400">✓</span>}
                  </button>
                </div>
              )}
            </div>
          </div>
          
          {isLoadingDocuments ? (
            <div className="text-center py-12 bg-slate-800 rounded-lg border border-slate-700">
              <div className="animate-spin w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4"></div>
              <p className="text-slate-400 mb-2">Loading your document library...</p>
              <p className="text-slate-500 text-sm">Fetching documents from database</p>
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-12 bg-slate-800 rounded-lg border border-slate-700">
              <FileText className="w-16 h-16 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400 mb-2">No documents in your library</p>
              <p className="text-slate-500 text-sm">Upload your first PDF to get started</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {sortedDocuments.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  document={doc}
                  onClick={() => isSelectMode ? toggleSelect(doc.id) : openDocument(doc.id)}
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
        </div>
      </div>

      {/* Select Mode Actions */}
      {isSelectMode && selectedDocuments.length > 0 && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-slate-800 rounded-lg shadow-lg p-4 border border-slate-600 z-50">
          <div className="flex items-center gap-4">
            <span className="text-white text-sm">
              {selectedDocuments.length} document{selectedDocuments.length !== 1 ? 's' : ''} selected
            </span>

            {selectedDocuments.length >= 2 && (
              <button
                onClick={handleMergeDocuments}
                className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
                </svg>
                Merge Documents
              </button>
            )}

            <button
              onClick={() => {
                setSelectedDocuments([]);
                setIsSelectMode(false);
              }}
              className="bg-slate-600 hover:bg-slate-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Merge Dialog */}
      {showMergeDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-6 w-full max-w-md mx-4 border border-slate-600">
            <h3 className="text-xl font-bold text-white mb-4">Merge Documents</h3>

            <div className="mb-4">
              <p className="text-slate-300 text-sm mb-2">
                Merging {selectedDocuments.length} documents into a single PDF.
              </p>

              <div className="mb-4">
                <label className="block text-slate-300 text-sm font-medium mb-2">
                  Output filename (optional):
                </label>
                <input
                  type="text"
                  value={mergeFileName}
                  onChange={(e) => setMergeFileName(e.target.value)}
                  placeholder="Leave empty for auto-generated name"
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <p className="text-slate-400 text-xs mt-1">
                  If empty, will be named "merged_pdf_1", "merged_pdf_2", etc.
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={executeMerge}
                disabled={isMerging}
                className="flex-1 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
              >
                {isMerging ? (
                  <>
                    <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Merging...
                  </>
                ) : (
                  'Merge Documents'
                )}
              </button>

              <button
                onClick={cancelMerge}
                disabled={isMerging}
                className="px-4 py-2 bg-slate-600 hover:bg-slate-700 disabled:bg-slate-700 text-white rounded-lg font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Split Dialog */}
      {showSplitDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-6 w-full max-w-2xl mx-4 border border-slate-600 max-h-[90vh] overflow-y-auto">
            <h3 className="text-xl font-bold text-white mb-4">Split Document</h3>

            <div className="mb-4">
              <p className="text-slate-300 text-sm mb-4">
                Splitting "{splitDocumentName}" ({splitDocumentPages} pages) into multiple PDFs.
              </p>

              {/* Number of splits */}
              <div className="mb-4">
                <label className="block text-slate-300 text-sm font-medium mb-2">
                  Number of splits:
                </label>
                <input
                  type="number"
                  min="2"
                  max="10"
                  value={numSplits}
                  onChange={(e) => updateNumSplits(parseInt(e.target.value) || 2)}
                  className="w-24 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              {/* Split ranges */}
              <div className="space-y-4">
                <h4 className="text-slate-300 font-medium">Configure page ranges:</h4>
                {splitRanges.map((range, index) => (
                  <div key={index} className="bg-slate-700 p-4 rounded-lg">
                    <h5 className="text-white font-medium mb-3">Split {index + 1}</h5>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {/* Name input */}
                      <div>
                        <label className="block text-slate-300 text-xs font-medium mb-1">
                          Name (optional):
                        </label>
                        <input
                          type="text"
                          value={range.name}
                          onChange={(e) => updateSplitRange(index, 'name', e.target.value)}
                          placeholder={`part_${index + 1}`}
                          className="w-full px-2 py-1 bg-slate-600 border border-slate-500 rounded text-white text-sm placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-purple-500"
                        />
                      </div>

                      {/* Start page */}
                      <div>
                        <label className="block text-slate-300 text-xs font-medium mb-1">
                          Start page:
                        </label>
                        <input
                          type="number"
                          min="1"
                          max={splitDocumentPages}
                          value={range.startPage}
                          onChange={(e) => updateSplitRange(index, 'startPage', parseInt(e.target.value) || 1)}
                          className="w-full px-2 py-1 bg-slate-600 border border-slate-500 rounded text-white text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
                        />
                      </div>

                      {/* End page */}
                      <div>
                        <label className="block text-slate-300 text-xs font-medium mb-1">
                          End page:
                        </label>
                        <input
                          type="number"
                          min="1"
                          max={splitDocumentPages}
                          value={range.endPage}
                          onChange={(e) => updateSplitRange(index, 'endPage', parseInt(e.target.value) || 1)}
                          className="w-full px-2 py-1 bg-slate-600 border border-slate-500 rounded text-white text-sm focus:outline-none focus:ring-1 focus:ring-purple-500"
                        />
                      </div>
                    </div>

                    <p className="text-slate-400 text-xs mt-2">
                      Pages {range.startPage}-{range.endPage} ({range.endPage - range.startPage + 1} pages)
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                onClick={executeSplit}
                disabled={isSplitting}
                className="flex-1 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
              >
                {isSplitting ? (
                  <>
                    <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Splitting...
                  </>
                ) : (
                  'Split Document'
                )}
              </button>

              <button
                onClick={cancelSplit}
                disabled={isSplitting}
                className="px-4 py-2 bg-slate-600 hover:bg-slate-700 disabled:bg-slate-700 text-white rounded-lg font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Persona/Job Form Modal */}
      <AIPersonaJobForm
        isVisible={showPersonaForm}
        onSubmit={handlePersonaJobSubmit}
        onCancel={() => setShowPersonaForm(false)}
        initialPersona={currentPersona}
        initialJob={currentJob}
      />

      {/* AI Chatbot */}
      <SimpleChatbot
        isMinimized={!showChatbot}
        onToggleMinimize={() => setShowChatbot(!showChatbot)}
      />
    </div>
  );
};

export default HomePage;