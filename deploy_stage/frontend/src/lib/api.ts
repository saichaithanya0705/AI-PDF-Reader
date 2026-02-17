/**
 * Authenticated API client for making requests to the backend
 * Automatically includes JWT token from Supabase session
 */
import { supabase } from './supabaseClient';
import { API_URL } from '../config';

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Get authentication headers with JWT token
 * @returns Headers object with Authorization token
 * @throws Error if user is not authenticated
 */
export async function getAuthHeaders(): Promise<HeadersInit> {
  const { data: { session } } = await supabase.auth.getSession();
  
  if (!session) {
    throw new ApiError('Not authenticated. Please login.', 401);
  }
  
  return {
    'Authorization': `Bearer ${session.access_token}`,
  };
}

/**
 * Make an authenticated API request
 * @param endpoint - API endpoint (e.g., '/api/documents')
 * @param options - Fetch options
 * @returns Response data
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  try {
    const authHeaders = await getAuthHeaders();
    
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
        ...options.headers,
      },
    });
    
    // Handle authentication errors
    if (response.status === 401) {
      // Token expired or invalid
      await supabase.auth.signOut();
      window.location.href = '/login';
      throw new ApiError('Session expired. Please login again.', 401);
    }
    
    // Handle other errors
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || response.statusText,
        response.status,
        errorData
      );
    }
    
    // Parse response
    const data = await response.json();
    return data;
    
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error('API request failed:', error);
    throw new ApiError('Network error. Please try again.', 0);
  }
}

/**
 * Upload file with authentication
 * @param endpoint - Upload endpoint
 * @param formData - FormData with file
 * @returns Upload response
 */
export async function uploadFile<T = any>(
  endpoint: string,
  formData: FormData
): Promise<T> {
  try {
    const authHeaders = await getAuthHeaders();
    
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        ...authHeaders,
        // Don't set Content-Type for FormData - browser sets it with boundary
      },
      body: formData,
    });
    
    if (response.status === 401) {
      await supabase.auth.signOut();
      window.location.href = '/login';
      throw new ApiError('Session expired. Please login again.', 401);
    }
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || response.statusText,
        response.status,
        errorData
      );
    }
    
    return await response.json();
    
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error('Upload failed:', error);
    throw new ApiError('Upload failed. Please try again.', 0);
  }
}

// =============================================================================
// Convenience methods for common operations
// =============================================================================

/**
 * Get all documents for current user
 */
export async function getAllDocuments() {
  return apiRequest('/api/documents');
}

/**
 * Get sorted documents
 */
export async function getSortedDocuments(sortBy: string = 'upload_date', sortOrder: string = 'desc') {
  return apiRequest(`/api/documents/sorted/${sortBy}?sort_order=${sortOrder}`);
}

/**
 * Get specific document by ID
 */
export async function getDocument(documentId: string) {
  return apiRequest(`/api/documents/${documentId}`);
}

/**
 * Upload document (active file)
 */
export async function uploadDocument(
  file: File,
  clientId: string,
  persona?: string,
  job?: string
) {
  const formData = new FormData();
  formData.append('file', file);
  
  const params = new URLSearchParams({ client_id: clientId });
  if (persona) params.append('persona', persona);
  if (job) params.append('job', job);
  
  return uploadFile(`/upload/active_file?${params.toString()}`, formData);
}

/**
 * Upload context files (bulk)
 */
export async function uploadContextFiles(
  files: File[],
  clientId: string,
  persona?: string,
  job?: string
) {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  
  const params = new URLSearchParams({ client_id: clientId });
  if (persona) params.append('persona', persona);
  if (job) params.append('job', job);
  
  return uploadFile(`/upload/context_files?${params.toString()}`, formData);
}

/**
 * Delete document
 */
export async function deleteDocument(documentId: string, hardDelete: boolean = false) {
  return apiRequest(`/api/documents/${documentId}?hard_delete=${hardDelete}`, {
    method: 'DELETE',
  });
}

/**
 * Delete all documents
 */
export async function deleteAllDocuments(hardDelete: boolean = false) {
  return apiRequest(`/api/documents/all?hard_delete=${hardDelete}`, {
    method: 'DELETE',
  });
}

/**
 * Get recommendations for document
 */
export async function getRecommendations(
  documentId: string,
  page: number = 1,
  persona?: string,
  job?: string,
  includeCrossDocument: boolean = true
) {
  const params = new URLSearchParams({
    page: page.toString(),
    include_cross_document: includeCrossDocument.toString(),
  });
  
  if (persona) params.append('persona', persona);
  if (job) params.append('job', job);
  
  return apiRequest(`/api/recommendations/${documentId}?${params.toString()}`);
}

/**
 * Get insights for document
 */
export async function getInsights(
  documentId: string,
  page: number = 1,
  persona?: string,
  job?: string
) {
  const params = new URLSearchParams({
    page: page.toString(),
  });
  
  if (persona) params.append('persona', persona);
  if (job) params.append('job', job);
  
  return apiRequest(`/api/insights/${documentId}?${params.toString()}`);
}

/**
 * Send chat message
 */
export async function sendChatMessage(
  message: string,
  documentId?: string,
  documentContext?: string,
  conversationHistory: Array<{ role: string; content: string }> = []
) {
  return apiRequest('/api/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      document_id: documentId,
      document_context: documentContext,
      conversation_history: conversationHistory,
    }),
  });
}

/**
 * Analyze text selection
 */
export async function analyzeTextSelection(
  selectedText: string,
  documentId: string,
  page: number,
  persona?: string,
  job?: string,
  includeCrossDocument: boolean = true
) {
  return apiRequest('/api/text-selection-analysis', {
    method: 'POST',
    body: JSON.stringify({
      selected_text: selectedText,
      document_id: documentId,
      page,
      persona,
      job,
      include_cross_document: includeCrossDocument,
    }),
  });
}

/**
 * Ask GPT about selected text
 */
export async function askGPT(
  selectedText: string,
  context?: string,
  persona?: string,
  job?: string
) {
  return apiRequest('/api/ask-gpt', {
    method: 'POST',
    body: JSON.stringify({
      selected_text: selectedText,
      context,
      persona,
      job,
    }),
  });
}

/**
 * Generate audio for text
 */
export async function generateAudio(
  text: string,
  voice: string = 'alloy',
  speed: number = 1.0
) {
  return apiRequest('/api/generate-audio', {
    method: 'POST',
    body: JSON.stringify({
      text,
      voice,
      speed,
    }),
  });
}

/**
 * Generate podcast
 */
export async function generatePodcast(
  content: string,
  documentId: string,
  page: number = 1,
  persona?: string,
  job?: string,
  includeRelated: boolean = true
) {
  return apiRequest('/api/generate-podcast', {
    method: 'POST',
    body: JSON.stringify({
      content,
      document_id: documentId,
      page,
      persona,
      job,
      include_related: includeRelated,
    }),
  });
}

// =============================================================================
// Public endpoints (no authentication required)
// =============================================================================

/**
 * Make a public API request (no authentication)
 */
export async function publicApiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || response.statusText,
        response.status,
        errorData
      );
    }
    
    return await response.json();
    
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error('API request failed:', error);
    throw new ApiError('Network error. Please try again.', 0);
  }
}

/**
 * Health check (public)
 */
export async function healthCheck() {
  return publicApiRequest('/health');
}

/**
 * Get config (public)
 */
export async function getConfig() {
  return publicApiRequest('/config');
}
