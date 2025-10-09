import React, { createContext, useContext, useState, useEffect } from 'react';
import { API_URL } from '../config';

export interface PDFDocument {
  id: string;
  name: string;
  uploadDate: Date;
  lastOpened?: Date | null;
  lastUploaded?: Date | null;
  url: string;
  thumbnail?: string;
  size: number;
  validation?: {
    isValid: boolean;
    issues: string[];
    warnings: string[];
    summary: string;
    severity: 'success' | 'warning' | 'error';
  };
}

export interface RelatedSection {
  id: string;
  title: string;
  snippet: string;
  page: number;
  relevance: number;
  documentId: string;
  documentName: string;
  bbox?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  enhanced_relevance?: number;
  intelligence_explanation?: string;
  file_path?: string;
}

export interface Insight {
  id: string;
  type: 'key-insight' | 'did-you-know' | 'counterpoint' | 'connection';
  title: string;
  content: string;
  relevance: number;
}

interface PDFContextType {
  documents: PDFDocument[];
  currentDocument: PDFDocument | null;
  relatedSections: RelatedSection[];
  crossDocumentSections: RelatedSection[];
  insights: Insight[];
  isOnline: boolean;
  isLoadingDocuments: boolean;
  uploadDocument: (file: File, client_id: string, persona?: string, job?: string) => Promise<string>;
  uploadBulkDocuments: (files: File[], client_id: string, persona?: string, job?: string, considerPrevious?: boolean) => Promise<string[]>;
  setCurrentDocument: (doc: PDFDocument) => void;
  getRelatedSections: (documentId: string, currentPage: number) => Promise<RelatedSection[]>;
  getInsights: (documentId: string, currentPage: number) => Promise<Insight[]>;
  askGPT: (selectedText: string, context: string) => Promise<string>;
  updateDocuments: (newDocs: PDFDocument[]) => void;
  fetchAllDocuments: () => Promise<void>;
  fetchSortedDocuments: (sortBy?: string, sortOrder?: string) => Promise<void>;
  deleteDocument: (documentId: string) => Promise<void>;
  deleteAllDocuments: (permanent?: boolean) => Promise<void>;
  renameDocument: (documentId: string, newName: string) => Promise<void>;
  classifyUserIntent: (userInput: string) => Promise<any>;
  getPersonaJobSuggestions: (userInput: string, topK?: number) => Promise<any>;
}

const PDFContext = createContext<PDFContextType | undefined>(undefined);

export const usePDF = () => {
  const context = useContext(PDFContext);
  if (!context) {
    throw new Error('usePDF must be used within a PDFProvider');
  }
  return context;
};

export const PDFProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [documents, setDocuments] = useState<PDFDocument[]>([]);
  const [currentDocument, setCurrentDocument] = useState<PDFDocument | null>(null);
  const [relatedSections, setRelatedSections] = useState<RelatedSection[]>([]);
  const [crossDocumentSections, setCrossDocumentSections] = useState<RelatedSection[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Load stored documents
    const stored = localStorage.getItem('pdf-documents');
    if (stored) {
      setDocuments(JSON.parse(stored));
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const BACKEND_URL = API_URL;

  const uploadDocument = async (file: File, client_id: string, persona?: string, job?: string): Promise<string> => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      if (persona) formData.append('persona', persona);
      if (job) formData.append('job', job);

      const response = await fetch(`${BACKEND_URL}/upload/active_file?client_id=${client_id}`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Upload error:', response.status, errorText);
        throw new Error(`Upload failed: ${response.statusText}`);
      }
      const data = await response.json();
      console.log('Upload success:', data);

      const document: PDFDocument = {
        id: data.job_id,
        name: file.name,
        uploadDate: new Date(),
        url: data.file_url ? `${BACKEND_URL}${data.file_url}` : URL.createObjectURL(file),
        size: file.size
      };

      const newDocuments = [...documents, document];
      setDocuments(newDocuments);
      localStorage.setItem('pdf-documents', JSON.stringify(newDocuments));
      console.log('Document added to state:', document);

      return data.job_id;
    } catch (error) {
      console.error('Upload failed:', error);
      throw error;
    }
  };

  const uploadBulkDocuments = async (files: File[], client_id: string, persona?: string, job?: string, considerPrevious?: boolean): Promise<string[]> => {
    try {
      const formData = new FormData();
      files.forEach(file => formData.append('files', file));
      if (persona) formData.append('persona', persona);
      if (job) formData.append('job', job);
      if (considerPrevious !== undefined) formData.append('consider_previous', considerPrevious.toString());

      const response = await fetch(`${BACKEND_URL}/upload/context_files?client_id=${client_id}`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Bulk upload error:', response.status, errorText);
        throw new Error(`Bulk upload failed: ${response.statusText}`);
      }
      const data = await response.json();
      console.log('Bulk upload success:', data);

      const newDocs: PDFDocument[] = files.map((file, index) => ({
        id: data.job_ids[index],
        name: file.name,
        uploadDate: new Date(),
        url: data.file_urls && data.file_urls[index] ? `${BACKEND_URL}${data.file_urls[index]}` : URL.createObjectURL(file),
        size: file.size
      }));

      const updatedDocuments = [...documents, ...newDocs];
      setDocuments(updatedDocuments);
      localStorage.setItem('pdf-documents', JSON.stringify(updatedDocuments));
      console.log('Bulk documents added to state:', newDocs);

      return data.job_ids;
    } catch (error) {
      console.error('Bulk upload failed:', error);
      throw error;
    }
  };

  const updateDocuments = (newDocs: PDFDocument[]) => {
    setDocuments(newDocs);
    localStorage.setItem('pdf-documents', JSON.stringify(newDocs));
  };

  const getRelatedSections = async (documentId: string, currentPage: number): Promise<RelatedSection[]> => {
    try {
      // Get persona and job from localStorage for intelligent recommendations
      const persona = localStorage.getItem('lastPersona') || 'Student';
      const job = localStorage.getItem('lastJob') || 'Learning and Research';
      
      const queryParams = new URLSearchParams({
        page: currentPage.toString(),
        include_cross_document: 'true'
      });
      
      // Always include persona and job (with defaults)
      queryParams.append('persona', persona);
      queryParams.append('job', job);
      
      const response = await fetch(`${BACKEND_URL}/api/recommendations/${documentId}?${queryParams}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch recommendations: ${response.statusText}`);
      }

      const data = await response.json();
      const sections = data.recommendations || [];
      const crossDocSections = data.cross_document_sections || [];

      console.log('📊 Related sections found:', {
        sameDocument: sections.length,
        crossDocument: crossDocSections.length,
        intelligenceEnabled: data.intelligence_enabled
      });

      setRelatedSections(sections);
      setCrossDocumentSections(crossDocSections);
      
      return sections;
    } catch (error) {
      console.error('Error fetching related sections:', error);

      // Fallback to mock data if API fails
      const mockSections: RelatedSection[] = [
        {
          id: '1',
          title: 'Introduction to Machine Learning',
          snippet: 'This section introduces fundamental concepts of machine learning algorithms and their applications in modern data science.',
          page: 5,
          relevance: 0.95,
          documentId: 'doc-1',
          documentName: 'AI Fundamentals.pdf'
        },
        {
          id: '2',
          title: 'Neural Network Architecture',
          snippet: 'Detailed explanation of neural network structures and how they process information through interconnected nodes.',
          page: 12,
          relevance: 0.87,
          documentId: 'doc-2',
          documentName: 'Deep Learning Guide.pdf'
        },
        {
          id: '3',
          title: 'Data Preprocessing Techniques',
          snippet: 'Essential methods for cleaning and preparing data before feeding it into machine learning models.',
          page: 3,
          relevance: 0.82,
          documentId: documentId,
          documentName: currentDocument?.name || 'Current Document'
        }
      ];

      setRelatedSections(mockSections);
      return mockSections;
    }
  };

  const getInsights = async (documentId: string, currentPage: number): Promise<Insight[]> => {
    if (!isOnline) {
      return [];
    }

    try {
      // For individual document insights, don't use persona/job - use comprehensive analysis
      const queryParams = new URLSearchParams({
        page: currentPage.toString()
      });

      console.log('🧠 Fetching comprehensive AI insights for document:', documentId, 'page:', currentPage);
      
      const response = await fetch(`${BACKEND_URL}/api/insights/${documentId}?${queryParams}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch insights: ${response.statusText}`);
      }

      const data = await response.json();
      const insights = data.insights || [];

      console.log('🧠 Received insights:', insights.length, 'comprehensive insights');

      setInsights(insights);
      return insights;
    } catch (error) {
      console.error('Error fetching insights:', error);

      // Fallback to mock data if API fails
      const mockInsights: Insight[] = [
        {
          id: '1',
          type: 'key-insight',
          title: 'Key Insight',
          content: 'Machine learning models require substantial amounts of quality data to achieve optimal performance and generalization.',
          relevance: 0.9
        },
        {
          id: '2',
          type: 'did-you-know',
          title: 'Did You Know?',
          content: 'The term "artificial intelligence" was first coined by John McCarthy in 1956 during the Dartmouth Conference.',
          relevance: 0.85
        },
        {
          id: '3',
          type: 'counterpoint',
          title: 'Counterpoint',
          content: 'While deep learning is powerful, traditional machine learning methods often outperform it on smaller datasets.',
          relevance: 0.78
        }
      ];

      setInsights(mockInsights);
      return mockInsights;
    }
  };

  const askGPT = async (selectedText: string, context: string): Promise<string> => {
    if (!isOnline) {
      throw new Error('Internet connection required for GPT insights');
    }

    try {
      const response = await fetch(`${BACKEND_URL}/api/ask-gpt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          selected_text: selectedText,
          context: context
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to get GPT response: ${response.statusText}`);
      }

      const data = await response.json();
      return data.response || 'No response available';
    } catch (error) {
      console.error('Error asking GPT:', error);

      // Fallback response
      return `This text discusses ${selectedText.slice(0, 50)}... which is a fundamental concept in the field. It relates to the broader context of the document by providing essential background information.`;
    }
  };

  // Fetch sorted documents from backend
  const fetchSortedDocuments = async (sortBy: string = 'upload_date', sortOrder: string = 'desc'): Promise<void> => {
    try {
      setIsLoadingDocuments(true);
      console.log(`📚 Fetching sorted documents: ${sortBy} ${sortOrder}`);

      const response = await fetch(`${BACKEND_URL}/api/documents/sorted/${sortBy}?sort_order=${sortOrder}`);

      if (response.ok) {
        const data = await response.json();
        console.log('📚 Sorted API Response:', data);

        if (data.documents && Array.isArray(data.documents)) {
          const formattedDocs: PDFDocument[] = data.documents.map((doc: any) => {
            // Same formatting logic as fetchAllDocuments
            let uploadDate: Date;
            let lastOpened: Date | null = null;
            let lastUploaded: Date | null = null;

            try {
              uploadDate = new Date(doc.upload_date || doc.uploadDate);
              if (isNaN(uploadDate.getTime())) uploadDate = new Date();
            } catch {
              uploadDate = new Date();
            }

            try {
              if (doc.last_opened || doc.last_accessed || doc.lastOpened) {
                lastOpened = new Date(doc.last_opened || doc.last_accessed || doc.lastOpened);
                if (isNaN(lastOpened.getTime())) lastOpened = null;
              }
            } catch {
              lastOpened = null;
            }

            try {
              if (doc.last_uploaded) {
                lastUploaded = new Date(doc.last_uploaded);
                if (isNaN(lastUploaded.getTime())) lastUploaded = null;
              }
            } catch {
              lastUploaded = null;
            }

            return {
              id: doc.id,
              name: doc.original_name || doc.name || doc.filename || 'Unknown Document',
              uploadDate,
              lastOpened,
              lastUploaded: lastUploaded || uploadDate,
              url: doc.url || `${BACKEND_URL}/api/files/${doc.filename}`,
              thumbnail: doc.thumbnail,
              size: doc.file_size || doc.size || 0,
              validation: doc.validation_result ? {
                isValid: doc.validation_result.isValid || doc.validation_result.is_valid,
                issues: doc.validation_result.issues || [],
                warnings: doc.validation_result.warnings || [],
                summary: doc.validation_result.summary || 'Unknown status',
                severity: doc.validation_result.severity || 'success'
              } : undefined
            };
          });

          setDocuments(formattedDocs);
          console.log(`✅ Sorted documents loaded: ${formattedDocs.length} (${sortBy} ${sortOrder})`);
          localStorage.removeItem('documents');
          setIsLoadingDocuments(false);
          return;
        }
      }
    } catch (error) {
      console.error('❌ Error fetching sorted documents:', error);
      // Fall back to regular fetch
      await fetchAllDocuments();
    } finally {
      setIsLoadingDocuments(false);
    }
  };

  // Fetch all documents from database
  const fetchAllDocuments = async (): Promise<void> => {
    try {
      setIsLoadingDocuments(true);
      console.log('📚 Fetching all documents from database...');
      console.log('📚 Backend URL:', BACKEND_URL);
      console.log('📚 Full URL:', `${BACKEND_URL}/api/documents`);

      const response = await fetch(`${BACKEND_URL}/api/documents`);
      console.log('📚 Response status:', response.status);
      console.log('📚 Response headers:', Object.fromEntries(response.headers.entries()));

      // Check if the response is HTML (404 page) instead of JSON
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        console.log('📚 Documents API endpoint not available - Content-Type:', contentType);
        console.log('📚 Response text:', await response.text());
        setIsLoadingDocuments(false);
        return;
      }

      if (!response.ok) {
        console.error(`❌ API request failed: ${response.status} ${response.statusText}`);
        const errorText = await response.text();
        console.error(`❌ Error response: ${errorText}`);
        throw new Error(`Failed to fetch documents: ${response.status}`);
      }

      const data = await response.json();
      console.log('📚 Raw API Response:', data);
      console.log('📚 Response type:', typeof data);
      console.log('📚 Response keys:', Object.keys(data));
      console.log('📚 Documents array:', data.documents);
      console.log('📚 Documents count from API:', data.count);
      console.log('📚 Total count from API:', data.total_count);
      console.log('📚 Stats from API:', data.stats);

      if (data.documents && Array.isArray(data.documents)) {
        const formattedDocs: PDFDocument[] = data.documents.map((doc: any) => {
          // Safe date parsing
          let uploadDate: Date;
          let lastOpened: Date | null = null;

          try {
            // Handle both ISO string and timestamp formats
            const dateStr = doc.upload_date || doc.uploadDate;
            uploadDate = new Date(dateStr);
            if (isNaN(uploadDate.getTime())) {
              uploadDate = new Date();
            }
          } catch {
            uploadDate = new Date();
          }

          try {
            if (doc.last_opened || doc.last_accessed || doc.lastOpened) {
              lastOpened = new Date(doc.last_opened || doc.last_accessed || doc.lastOpened);
              if (isNaN(lastOpened.getTime())) {
                lastOpened = null;
              }
            }
          } catch {
            lastOpened = null;
          }

          // Parse last uploaded time
          let lastUploaded: Date | null = null;
          try {
            if (doc.last_uploaded) {
              lastUploaded = new Date(doc.last_uploaded);
              if (isNaN(lastUploaded.getTime())) {
                lastUploaded = null;
              }
            }
          } catch {
            lastUploaded = null;
          }

          return {
            id: doc.id,
            name: doc.original_name || doc.name || doc.filename || 'Unknown Document',
            uploadDate,
            lastOpened,
            lastUploaded: lastUploaded || uploadDate, // Fallback to upload date
            url: doc.url || `${BACKEND_URL}/api/files/${doc.filename}`,
            thumbnail: doc.thumbnail,
            size: doc.file_size || doc.size || 0,
            validation: doc.validation_result ? {
              isValid: doc.validation_result.isValid || doc.validation_result.is_valid,
              issues: doc.validation_result.issues || [],
              warnings: doc.validation_result.warnings || [],
              summary: doc.validation_result.summary || 'Unknown status',
              severity: doc.validation_result.severity || 'success'
            } : undefined
          };
        });

        setDocuments(formattedDocs);
        console.log('✅ Documents loaded from database:', formattedDocs.length);
        console.log('📊 Database stats:', data.stats);

        // Clear localStorage since we're now using database
        localStorage.removeItem('documents');
      } else {
        console.log('📚 No documents found in database');
        setDocuments([]);
      }
    } catch (error) {
      console.error('❌ Error fetching documents from main API:', error);

      // Try emergency API as fallback
      try {
        console.log('🚨 Trying emergency API fallback...');
        const emergencyResponse = await fetch('http://localhost:8081/emergency/documents');

        if (emergencyResponse.ok) {
          const emergencyData = await emergencyResponse.json();
          console.log('🚨 Emergency API Response:', emergencyData);

          if (emergencyData.documents && Array.isArray(emergencyData.documents)) {
            const formattedDocs: PDFDocument[] = emergencyData.documents.map((doc: any) => {
              let uploadDate: Date;
              try {
                uploadDate = new Date(doc.upload_date);
                if (isNaN(uploadDate.getTime())) uploadDate = new Date();
              } catch {
                uploadDate = new Date();
              }

              return {
                id: doc.id,
                name: doc.original_name || doc.filename || 'Unknown Document',
                uploadDate,
                lastOpened: null,
                url: doc.url || `${BACKEND_URL}/api/files/${doc.filename}`,
                thumbnail: doc.thumbnail,
                size: doc.file_size || 0
              };
            });

            setDocuments(formattedDocs);
            console.log('✅ Documents loaded from emergency API:', formattedDocs.length);
            setIsLoadingDocuments(false);
            return;
          }
        }
      } catch (emergencyError) {
        console.error('❌ Emergency API also failed:', emergencyError);
      }

      console.log('📚 Falling back to local storage documents');
      // Don't clear existing documents on error, just log it
    } finally {
      setIsLoadingDocuments(false);
    }
  };

  // Delete a document
  const deleteDocument = async (documentId: string): Promise<void> => {
    try {
      console.log('🗑️ Deleting document:', documentId);

      try {
        const response = await fetch(`${BACKEND_URL}/api/documents/${documentId}`, {
          method: 'DELETE'
        });

        // Check if the response is HTML (404 page) instead of JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          console.log('🗑️ Delete API endpoint not available, removing from local state only');
        } else if (!response.ok) {
          throw new Error(`Failed to delete document: ${response.status}`);
        } else {
          const data = await response.json();
          console.log('✅ Document deleted from backend:', data.message);
        }
      } catch (fetchError) {
        console.log('🗑️ Backend delete failed, removing from local state only:', fetchError);
      }

      // Remove from local state regardless of backend response
      setDocuments(prev => prev.filter(doc => doc.id !== documentId));

      // Clear current document if it was deleted
      if (currentDocument?.id === documentId) {
        setCurrentDocument(null);
      }

      console.log('✅ Document removed from local state');
    } catch (error) {
      console.error('❌ Error deleting document:', error);
      throw error; // Re-throw to handle in UI
    }
  };

  // Delete all documents
  const deleteAllDocuments = async (permanent: boolean = false): Promise<void> => {
    try {
      console.log('🗑️ Deleting all documents, permanent:', permanent);

      try {
        const response = await fetch(`${BACKEND_URL}/api/documents?permanent=${permanent}`, {
          method: 'DELETE'
        });

        if (!response.ok) {
          throw new Error(`Failed to delete all documents: ${response.status}`);
        }

        const data = await response.json();
        console.log('✅ All documents deleted from backend:', data.message);
      } catch (fetchError) {
        console.log('🗑️ Backend delete all failed, clearing local state only:', fetchError);
      }

      // Clear all documents from local state
      setDocuments([]);
      setCurrentDocument(null);

      // Clear localStorage backup
      localStorage.removeItem('pdf-documents');
      localStorage.removeItem('documents');

      console.log('✅ All documents removed from local state');
    } catch (error) {
      console.error('❌ Error deleting all documents:', error);
      throw error;
    }
  };

  // Rename a document
  const renameDocument = async (documentId: string, newName: string): Promise<void> => {
    try {
      console.log('✏️ Renaming document:', documentId, 'to:', newName);

      // Find the document to get old name for rollback
      const document = documents.find(doc => doc.id === documentId);
      if (!document) {
        throw new Error('Document not found');
      }

      const oldName = document.name;

      // Update frontend state immediately for better UX (optimistic update)
      setDocuments(prev => prev.map(doc =>
        doc.id === documentId ? { ...doc, name: newName.trim() } : doc
      ));

      try {
        const response = await fetch(`${BACKEND_URL}/api/documents/${documentId}/rename?new_name=${encodeURIComponent(newName)}`, {
          method: 'PUT'
        });

        if (!response.ok) {
          throw new Error(`Failed to rename document: ${response.status}`);
        }

        const data = await response.json();
        console.log('✅ Document renamed in backend:', data.message);

        // Update with the actual response data if available
        if (data.document) {
          const updatedDoc: PDFDocument = {
            id: data.document.id,
            name: data.document.original_name || data.document.name,
            uploadDate: new Date(data.document.upload_date || data.document.uploadDate),
            lastOpened: data.document.last_opened ? new Date(data.document.last_opened) : null,
            lastUploaded: data.document.last_uploaded ? new Date(data.document.last_uploaded) : null,
            url: data.document.url,
            size: data.document.file_size || data.document.size || 0,
            validation: data.document.validation_result
          };

          setDocuments(prev => prev.map(doc =>
            doc.id === documentId ? updatedDoc : doc
          ));
        }

      } catch (fetchError) {
        console.error('🗑️ Backend rename failed, reverting local state:', fetchError);
        
        // Revert the optimistic update
        setDocuments(prev => prev.map(doc =>
          doc.id === documentId ? { ...doc, name: oldName } : doc
        ));
        
        throw fetchError;
      }

      console.log('✅ Document renamed successfully');
    } catch (error) {
      console.error('❌ Error renaming document:', error);
      throw error;
    }
  };

  const classifyUserIntent = async (userInput: string) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/classify-intent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_input: userInput,
          include_suggestions: true
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('🤖 Intent classification result:', data);
      return data;
    } catch (error) {
      console.error('❌ Error classifying user intent:', error);
      throw error;
    }
  };

  const getPersonaJobSuggestions = async (userInput: string, topK: number = 3) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/persona-job-suggestions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_input: userInput,
          top_k: topK
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('🔍 Persona/job suggestions:', data);
      return data;
    } catch (error) {
      console.error('❌ Error getting suggestions:', error);
      throw error;
    }
  };

  return (
    <PDFContext.Provider
      value={{
        documents,
        currentDocument,
        relatedSections,
        crossDocumentSections,
        insights,
        isOnline,
        isLoadingDocuments,
        uploadDocument,
        uploadBulkDocuments,
        setCurrentDocument,
        getRelatedSections,
        getInsights,
        askGPT,
        updateDocuments,
        fetchAllDocuments,
        fetchSortedDocuments,
        deleteDocument,
        deleteAllDocuments,
        renameDocument,
        classifyUserIntent,
        getPersonaJobSuggestions
      }}
    >
      {children}
    </PDFContext.Provider>
  );
};