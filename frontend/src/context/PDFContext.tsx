import React, { createContext, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { API_URL } from '../config';
import {
  askGPT as askGPTApi,
  deleteAllDocuments as deleteAllDocumentsApi,
  deleteDocument as deleteDocumentApi,
  getAllDocuments as getAllDocumentsApi,
  getDocument as getDocumentApi,
  getInsights as getInsightsApi,
  getRecommendations as getRecommendationsApi,
  updateDocumentMetadata,
  uploadContextFiles,
  uploadDocument as uploadDocumentApi,
} from '../lib/api';
import {
  getBulkUploadedDocumentSeeds,
  normalizeBulkUploadResponse,
  type BulkUploadResult,
} from './bulkUploadContract';

type UnknownRecord = Record<string, unknown>;

interface ClassificationOption {
  persona: string;
  job: string;
  keywords: string[];
}

export interface PDFDocument {
  id: string;
  name: string;
  uploadDate: Date;
  lastOpened?: Date | null;
  lastUploaded?: Date | null;
  url: string;
  thumbnail?: string;
  size: number;
  metadata?: UnknownRecord;
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

// Must stay in sync with the insight types emitted by backend/app/enhanced_llm_service.py.
const INSIGHT_TYPES = [
  'key-insight',
  'key-takeaway',
  'did-you-know',
  'counterpoint',
  'connection',
  'practical-tip',
  'deep-dive',
  'study-tip',
] as const;

export interface Insight {
  id: string;
  type: typeof INSIGHT_TYPES[number];
  title: string;
  content: string;
  relevance: number;
}

interface ActiveUploadResult {
  job_id: string;
  file_url?: string;
}

export interface BulkUploadContextResult extends BulkUploadResult {
  documents: PDFDocument[];
}

interface PDFContextType {
  documents: PDFDocument[];
  currentDocument: PDFDocument | null;
  relatedSections: RelatedSection[];
  crossDocumentSections: RelatedSection[];
  insights: Insight[];
  isOnline: boolean;
  isLoadingDocuments: boolean;
  uploadDocument: (file: File, clientId: string, persona?: string, job?: string) => Promise<string>;
  uploadBulkDocuments: (files: File[], clientId: string, persona?: string, job?: string, considerPrevious?: boolean) => Promise<BulkUploadContextResult>;
  setCurrentDocument: (doc: PDFDocument | null) => void;
  loadDocument: (documentId: string) => Promise<PDFDocument | null>;
  getRelatedSections: (documentId: string, currentPage: number) => Promise<RelatedSection[]>;
  getInsights: (documentId: string, currentPage: number) => Promise<Insight[]>;
  clearRelatedContent: () => void;
  askGPT: (selectedText: string, context: string) => Promise<string>;
  updateDocuments: (newDocs: PDFDocument[]) => void;
  fetchAllDocuments: () => Promise<void>;
  fetchSortedDocuments: (sortBy?: string, sortOrder?: string) => Promise<void>;
  deleteDocument: (documentId: string) => Promise<void>;
  deleteAllDocuments: (permanent?: boolean) => Promise<void>;
  renameDocument: (documentId: string, newName: string) => Promise<void>;
  classifyUserIntent: (userInput: string) => Promise<ReturnType<typeof classifyIntentLocally>>;
  getPersonaJobSuggestions: (userInput: string, topK?: number) => Promise<unknown>;
}

export const PDFContext = createContext<PDFContextType | undefined>(undefined);

const isRecord = (value: unknown): value is UnknownRecord => (
  typeof value === 'object' && value !== null
);

const asString = (value: unknown): string | undefined => (
  typeof value === 'string' && value.trim().length > 0 ? value : undefined
);

const asNumber = (value: unknown, fallback = 0): number => {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }
  return fallback;
};

const asBoolean = (value: unknown, fallback = false): boolean => (
  typeof value === 'boolean' ? value : fallback
);

const CLASSIFICATION_OPTIONS: ClassificationOption[] = [
  {
    persona: 'Undergraduate Chemistry Student',
    job: 'Identify key concepts and mechanisms for exam preparation',
    keywords: ['chemistry', 'exam', 'reaction', 'molecule', 'mechanism', 'organic', 'inorganic'],
  },
  {
    persona: 'Graduate Research Student',
    job: 'Extract research methodologies and findings',
    keywords: ['research', 'paper', 'methodology', 'findings', 'literature', 'experiment', 'study'],
  },
  {
    persona: 'Travel Planner',
    job: 'Plan trip itineraries and budget allocation',
    keywords: ['travel', 'trip', 'itinerary', 'hotel', 'flight', 'budget', 'destination'],
  },
  {
    persona: 'HR Professional',
    job: 'Review compliance requirements and procedures',
    keywords: ['hr', 'employee', 'policy', 'compliance', 'hiring', 'benefits', 'procedure'],
  },
  {
    persona: 'Legal Professional',
    job: 'Review contract terms and legal obligations',
    keywords: ['legal', 'contract', 'clause', 'agreement', 'law', 'obligation', 'liability'],
  },
  {
    persona: 'Software Engineer',
    job: 'Understand technical specifications and APIs',
    keywords: ['software', 'api', 'code', 'technical', 'system', 'architecture', 'developer'],
  },
  {
    persona: 'Financial Analyst',
    job: 'Analyze financial data and trends',
    keywords: ['finance', 'financial', 'revenue', 'cost', 'forecast', 'market', 'investment'],
  },
  {
    persona: 'General Reader',
    job: 'General understanding and learning',
    keywords: [],
  },
];

const classifyIntentLocally = (userInput: string) => {
  const normalizedInput = userInput.toLowerCase();
  const scoredOptions = CLASSIFICATION_OPTIONS
    .map((option) => ({
      option,
      score: option.keywords.filter((keyword) => normalizedInput.includes(keyword)).length,
    }))
    .sort((a, b) => b.score - a.score);
  const bestMatch = scoredOptions[0]?.score > 0
    ? scoredOptions[0]
    : scoredOptions.find((entry) => entry.option.persona === 'General Reader') || scoredOptions[0];
  const confidence = bestMatch.score > 2 ? 0.86 : bestMatch.score > 0 ? 0.68 : 0.55;

  return {
    status: 'success',
    classification: {
      persona: {
        name: bestMatch.option.persona,
        confidence,
        reasoning: 'Matched the request against the supported local persona/job profiles.',
      },
      job: {
        name: bestMatch.option.job,
        confidence,
        reasoning: 'Selected the closest task profile for the described reading goal.',
      },
      combined_confidence: confidence,
      suggestions: [
        'Review and adjust the persona/job before uploading if the match feels off.',
      ],
      alternatives: {
        personas: scoredOptions.slice(0, 3).map(({ option, score }) => ({
          name: option.persona,
          confidence: score > 0 ? Math.min(0.85, 0.5 + score * 0.12) : 0.45,
        })),
        jobs: scoredOptions.slice(0, 3).map(({ option, score }) => ({
          name: option.job,
          confidence: score > 0 ? Math.min(0.85, 0.5 + score * 0.12) : 0.45,
        })),
      },
    },
  };
};

const parseDate = (value: unknown, fallback = new Date()): Date => {
  const text = typeof value === 'string' || typeof value === 'number' ? value : undefined;
  if (text === undefined) return fallback;
  const date = new Date(text);
  return Number.isNaN(date.getTime()) ? fallback : date;
};

const parseOptionalDate = (value: unknown): Date | null => {
  if (value === null || value === undefined || value === '') return null;
  const date = parseDate(value, new Date(Number.NaN));
  return Number.isNaN(date.getTime()) ? null : date;
};

const readMetadata = (value: unknown): UnknownRecord | undefined => (
  isRecord(value) ? value : undefined
);

const readStringArray = (value: unknown): string[] => (
  Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === 'string') : []
);

const getDisplayName = (record: UnknownRecord): string => {
  const metadata = readMetadata(record.metadata);
  return (
    asString(metadata?.display_name) ||
    asString(record.original_name) ||
    asString(record.name) ||
    asString(record.filename) ||
    'Unknown Document'
  );
};

const normalizeBackendUrl = (fileUrl: unknown, filename: unknown, fallbackUrl = '') => {
  const url = asString(fileUrl);
  if (url) {
    if (/^(https?:|blob:)/i.test(url)) return url;
    return `${API_URL}${url.startsWith('/') ? url : `/${url}`}`;
  }

  const fileName = asString(filename);
  if (fileName) {
    return `${API_URL}/api/files/${encodeURIComponent(fileName)}`;
  }

  return fallbackUrl;
};

const normalizeValidation = (value: unknown): PDFDocument['validation'] | undefined => {
  if (!isRecord(value)) return undefined;
  const severity = asString(value.severity);

  return {
    isValid: asBoolean(value.isValid, asBoolean(value.is_valid, true)),
    issues: readStringArray(value.issues),
    warnings: readStringArray(value.warnings),
    summary: asString(value.summary) || 'Unknown status',
    severity: severity === 'warning' || severity === 'error' ? severity : 'success',
  };
};

const formatBackendDocument = (record: UnknownRecord, fallbackUrl = ''): PDFDocument | null => {
  const id = asString(record.id);
  if (!id) return null;

  const uploadDate = parseDate(record.upload_date ?? record.uploadDate);
  const metadata = readMetadata(record.metadata);

  return {
    id,
    name: getDisplayName(record),
    uploadDate,
    lastOpened: parseOptionalDate(record.last_opened ?? record.last_accessed ?? record.lastOpened),
    lastUploaded: parseOptionalDate(record.last_uploaded ?? record.lastUploaded) || uploadDate,
    url: normalizeBackendUrl(record.url, record.filename, fallbackUrl),
    thumbnail: asString(record.thumbnail),
    size: asNumber(record.file_size ?? record.size),
    metadata,
    validation: normalizeValidation(record.validation_result),
  };
};

const mergeDocumentsById = (existingDocuments: PDFDocument[], incomingDocuments: PDFDocument[]) => {
  const merged = [...existingDocuments];

  incomingDocuments.forEach((incomingDocument) => {
    const index = merged.findIndex((document) => document.id === incomingDocument.id);
    if (index >= 0) {
      merged[index] = { ...merged[index], ...incomingDocument };
    } else {
      merged.push(incomingDocument);
    }
  });

  return merged;
};

const normalizeDocumentsResponse = (data: unknown): PDFDocument[] => {
  if (!isRecord(data) || !Array.isArray(data.documents)) return [];

  return data.documents
    .filter(isRecord)
    .map((record) => formatBackendDocument(record))
    .filter((document): document is PDFDocument => Boolean(document));
};

const normalizeDocumentResponse = (data: unknown): PDFDocument | null => {
  if (!isRecord(data)) return null;
  const record = isRecord(data.document) ? data.document : data;
  return formatBackendDocument(record);
};

const normalizeRelatedSection = (record: UnknownRecord, fallbackDocumentId: string): RelatedSection | null => {
  const documentId = asString(record.documentId ?? record.document_id) || fallbackDocumentId;
  const page = asNumber(record.page ?? record.page_number, 1);
  const id = asString(record.id) || `${documentId}-${page}-${asString(record.title) || 'section'}`;
  const enhancedRelevance = record.enhanced_relevance === undefined
    ? undefined
    : asNumber(record.enhanced_relevance);

  return {
    id,
    title: asString(record.title) || asString(record.section_title) || 'Related section',
    snippet: asString(record.snippet) || asString(record.text) || '',
    page,
    relevance: asNumber(record.relevance ?? record.relevance_score ?? record.similarity, 0),
    documentId,
    documentName: asString(record.documentName ?? record.document_name) || 'Document',
    enhanced_relevance: enhancedRelevance,
    intelligence_explanation: asString(record.intelligence_explanation),
    file_path: asString(record.file_path),
  };
};

const normalizeSections = (value: unknown, fallbackDocumentId: string): RelatedSection[] => (
  Array.isArray(value)
    ? value
      .filter(isRecord)
      .map((record) => normalizeRelatedSection(record, fallbackDocumentId))
      .filter((section): section is RelatedSection => Boolean(section))
    : []
);

// Cross-document sections must name the PDF they came from. Falling back to the
// open document would render a match that navigates back to the same file.
const normalizeCrossDocumentSections = (value: unknown, currentDocumentId: string): RelatedSection[] => (
  normalizeSections(value, '').filter((section) => (
    section.documentId.length > 0 && section.documentId !== currentDocumentId
  ))
);

const normalizeInsights = (value: unknown): Insight[] => {
  if (!Array.isArray(value)) return [];

  const allowedTypes = new Set<Insight['type']>(INSIGHT_TYPES);

  return value.filter(isRecord).map((record, index) => {
    const type = asString(record.type);
    const normalizedType = allowedTypes.has(type as Insight['type'])
      ? type as Insight['type']
      : 'key-insight';

    return {
      id: asString(record.id) || `insight-${index}`,
      type: normalizedType,
      title: asString(record.title) || 'Insight',
      content: asString(record.content) || asString(record.text) || '',
      relevance: asNumber(record.relevance, 0),
    };
  });
};

const sortDocuments = (documents: PDFDocument[], sortBy: string, sortOrder: string) => {
  const direction = sortOrder === 'asc' ? 1 : -1;
  const getTime = (date: Date | null | undefined) => date?.getTime() || 0;

  return [...documents].sort((a, b) => {
    switch (sortBy) {
      case 'name':
      case 'nameAZ':
        return direction * a.name.localeCompare(b.name);
      case 'size':
        return direction * (a.size - b.size);
      case 'last_opened':
      case 'recentlyOpened':
        return direction * (getTime(a.lastOpened) - getTime(b.lastOpened));
      case 'last_uploaded':
      case 'recentlyUploaded':
      case 'upload_date':
      default:
        return direction * (getTime(a.lastUploaded || a.uploadDate) - getTime(b.lastUploaded || b.uploadDate));
    }
  });
};

const parseActiveUploadResult = (data: unknown): ActiveUploadResult => {
  if (!isRecord(data) || typeof data.job_id !== 'string' || data.job_id.trim().length === 0) {
    throw new Error('Upload response did not include a valid document id');
  }

  return {
    job_id: data.job_id,
    file_url: asString(data.file_url),
  };
};

export const PDFProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [documents, setDocuments] = useState<PDFDocument[]>([]);
  const [currentDocument, setCurrentDocument] = useState<PDFDocument | null>(null);
  const [relatedSections, setRelatedSections] = useState<RelatedSection[]>([]);
  const [crossDocumentSections, setCrossDocumentSections] = useState<RelatedSection[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  // Page turns fire overlapping requests; only the latest one may update state,
  // otherwise a slow response for page N overwrites the panel for page N+1.
  const relatedRequestRef = useRef(0);
  const insightsRequestRef = useRef(0);

  const persistDocuments = useCallback((nextDocuments: PDFDocument[]) => {
    setDocuments(nextDocuments);
    localStorage.setItem('pdf-documents', JSON.stringify(nextDocuments));
  }, []);

  const mergeAndPersistDocuments = useCallback((incomingDocuments: PDFDocument[]) => {
    setDocuments((previousDocuments) => {
      const nextDocuments = mergeDocumentsById(previousDocuments, incomingDocuments);
      localStorage.setItem('pdf-documents', JSON.stringify(nextDocuments));
      return nextDocuments;
    });
  }, []);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    const stored = localStorage.getItem('pdf-documents');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          const restored = parsed
            .filter(isRecord)
            .map((record) => formatBackendDocument(record, asString(record.url) || ''))
            .filter((document): document is PDFDocument => Boolean(document));
          setDocuments(restored);
        }
      } catch (error) {
        console.warn('Failed to restore cached PDF documents:', error);
        localStorage.removeItem('pdf-documents');
      }
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const uploadDocument = useCallback(async (file: File, clientId: string, persona?: string, job?: string): Promise<string> => {
    const data = await uploadDocumentApi(file, clientId, persona, job);
    const uploadResult = parseActiveUploadResult(data);

    const document: PDFDocument = {
      id: uploadResult.job_id,
      name: file.name,
      uploadDate: new Date(),
      lastUploaded: new Date(),
      url: normalizeBackendUrl(uploadResult.file_url, undefined, URL.createObjectURL(file)),
      size: file.size,
    };

    mergeAndPersistDocuments([document]);
    return uploadResult.job_id;
  }, [mergeAndPersistDocuments]);

  const uploadBulkDocuments = useCallback(async (
    files: File[],
    clientId: string,
    persona?: string,
    job?: string,
    considerPrevious?: boolean
  ): Promise<BulkUploadContextResult> => {
    const data = await uploadContextFiles(files, clientId, persona, job, considerPrevious);
    const uploadResult = normalizeBulkUploadResponse(data, files);

    const newDocuments: PDFDocument[] = getBulkUploadedDocumentSeeds(uploadResult, files)
      .map((seed) => {
        const fallbackUrl = seed.fileUrl
          ? ''
          : typeof File !== 'undefined' && seed.sourceFile instanceof File
            ? URL.createObjectURL(seed.sourceFile)
            : '';

        return {
          id: seed.id,
          name: seed.name,
          uploadDate: new Date(),
          lastUploaded: new Date(),
          url: normalizeBackendUrl(seed.fileUrl, undefined, fallbackUrl),
          size: seed.size,
        };
      });

    mergeAndPersistDocuments(newDocuments);

    return {
      ...uploadResult,
      documents: newDocuments,
    };
  }, [mergeAndPersistDocuments]);

  const updateDocuments = useCallback((newDocs: PDFDocument[]) => {
    persistDocuments(newDocs);
  }, [persistDocuments]);

  const fetchAllDocuments = useCallback(async (): Promise<void> => {
    setIsLoadingDocuments(true);
    try {
      const data = await getAllDocumentsApi();
      persistDocuments(normalizeDocumentsResponse(data));
      localStorage.removeItem('documents');
    } catch (error) {
      console.error('Error fetching documents from API:', error);
    } finally {
      setIsLoadingDocuments(false);
    }
  }, [persistDocuments]);

  const fetchSortedDocuments = useCallback(async (sortBy = 'upload_date', sortOrder = 'desc'): Promise<void> => {
    setIsLoadingDocuments(true);
    try {
      const data = await getAllDocumentsApi();
      const formattedDocuments = normalizeDocumentsResponse(data);
      persistDocuments(sortDocuments(formattedDocuments, sortBy, sortOrder));
      localStorage.removeItem('documents');
    } catch (error) {
      console.error('Error fetching sorted documents:', error);
    } finally {
      setIsLoadingDocuments(false);
    }
  }, [persistDocuments]);

  const loadDocument = useCallback(async (documentId: string): Promise<PDFDocument | null> => {
    try {
      const data = await getDocumentApi(documentId);
      const document = normalizeDocumentResponse(data);
      if (!document) {
        return null;
      }

      mergeAndPersistDocuments([document]);
      setCurrentDocument(document);
      return document;
    } catch (error) {
      console.error('Error loading document:', error);
      return null;
    }
  }, [mergeAndPersistDocuments]);

  const getRelatedSections = useCallback(async (documentId: string, currentPage: number): Promise<RelatedSection[]> => {
    const requestId = ++relatedRequestRef.current;
    try {
      // Only send persona/job the user actually chose; invented defaults pollute
      // the retrieval query and trigger keyword re-ranking on every page.
      const persona = localStorage.getItem('lastPersona') || undefined;
      const job = localStorage.getItem('lastJob') || undefined;
      const data = await getRecommendationsApi(documentId, currentPage, persona, job, true);
      if (requestId !== relatedRequestRef.current) return [];
      const response = isRecord(data) ? data : {};
      const sections = normalizeSections(response.recommendations, documentId);
      const crossDocSections = normalizeCrossDocumentSections(response.cross_document_sections, documentId);

      setRelatedSections(sections);
      setCrossDocumentSections(crossDocSections);
      return sections;
    } catch (error) {
      if (requestId !== relatedRequestRef.current) return [];
      console.error('Error fetching related sections:', error);
      setRelatedSections([]);
      setCrossDocumentSections([]);
      return [];
    }
  }, []);

  const clearRelatedContent = useCallback(() => {
    relatedRequestRef.current += 1;
    insightsRequestRef.current += 1;
    setRelatedSections([]);
    setCrossDocumentSections([]);
    setInsights([]);
  }, []);

  const getInsights = useCallback(async (documentId: string, currentPage: number): Promise<Insight[]> => {
    if (!isOnline) {
      return [];
    }

    const requestId = ++insightsRequestRef.current;
    try {
      const data = await getInsightsApi(
        documentId,
        currentPage,
        localStorage.getItem('lastPersona') || undefined,
        localStorage.getItem('lastJob') || undefined,
      );
      if (requestId !== insightsRequestRef.current) return [];
      const response = isRecord(data) ? data : {};
      const normalizedInsights = normalizeInsights(response.insights);

      setInsights(normalizedInsights);
      return normalizedInsights;
    } catch (error) {
      if (requestId !== insightsRequestRef.current) return [];
      console.error('Error fetching insights:', error);
      setInsights([]);
      return [];
    }
  }, [isOnline]);

  const askGPT = useCallback(async (selectedText: string, context: string): Promise<string> => {
    if (!isOnline) {
      throw new Error('Internet connection required for GPT insights');
    }

    try {
      const data = await askGPTApi(selectedText, context);
      const response = isRecord(data) ? data : {};
      return asString(response.response) || 'No response available';
    } catch (error) {
      console.error('Error asking GPT:', error);
      throw new Error('Unable to get GPT response right now');
    }
  }, [isOnline]);

  const deleteDocument = useCallback(async (documentId: string): Promise<void> => {
    await deleteDocumentApi(documentId, false);

    setDocuments((previousDocuments) => {
      const nextDocuments = previousDocuments.filter((document) => document.id !== documentId);
      localStorage.setItem('pdf-documents', JSON.stringify(nextDocuments));
      return nextDocuments;
    });

    setCurrentDocument((previousDocument) => (
      previousDocument?.id === documentId ? null : previousDocument
    ));
  }, []);

  const deleteAllDocuments = useCallback(async (permanent = false): Promise<void> => {
    const documentIds = documents.map((document) => document.id);
    await deleteAllDocumentsApi(documentIds, permanent);
    persistDocuments([]);
    setCurrentDocument(null);
    localStorage.removeItem('documents');
  }, [documents, persistDocuments]);

  const renameDocument = useCallback(async (documentId: string, newName: string): Promise<void> => {
    const trimmedName = newName.trim();
    if (!trimmedName) {
      throw new Error('Document name cannot be empty');
    }

    const existingDocument = documents.find((document) => document.id === documentId);
    if (!existingDocument) {
      throw new Error('Document not found');
    }

    const metadata = {
      ...(existingDocument.metadata || {}),
      display_name: trimmedName,
    };

    const optimisticDocument = { ...existingDocument, name: trimmedName, metadata };
    mergeAndPersistDocuments([optimisticDocument]);

    try {
      await updateDocumentMetadata(documentId, metadata);
    } catch (error) {
      mergeAndPersistDocuments([existingDocument]);
      throw error;
    }
  }, [documents, mergeAndPersistDocuments]);

  const classifyUserIntent = useCallback(async (userInput: string) => (
    classifyIntentLocally(userInput)
  ), []);

  const getPersonaJobSuggestions = useCallback(async (userInput: string, topK = 3) => (
    classifyIntentLocally(userInput).classification.alternatives.jobs.slice(0, topK)
  ), []);

  const value = useMemo<PDFContextType>(() => ({
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
    loadDocument,
    getRelatedSections,
    getInsights,
    clearRelatedContent,
    askGPT,
    updateDocuments,
    fetchAllDocuments,
    fetchSortedDocuments,
    deleteDocument,
    deleteAllDocuments,
    renameDocument,
    classifyUserIntent,
    getPersonaJobSuggestions,
  }), [
    documents,
    currentDocument,
    relatedSections,
    crossDocumentSections,
    insights,
    isOnline,
    isLoadingDocuments,
    uploadDocument,
    uploadBulkDocuments,
    loadDocument,
    getRelatedSections,
    getInsights,
    clearRelatedContent,
    askGPT,
    updateDocuments,
    fetchAllDocuments,
    fetchSortedDocuments,
    deleteDocument,
    deleteAllDocuments,
    renameDocument,
    classifyUserIntent,
    getPersonaJobSuggestions,
  ]);

  return (
    <PDFContext.Provider value={value}>
      {children}
    </PDFContext.Provider>
  );
};
