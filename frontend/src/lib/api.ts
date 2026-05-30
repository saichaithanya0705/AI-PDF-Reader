/**
 * Authenticated API client for backend requests.
 *
 * Production identity comes from Supabase JWTs. The only client_id fallback is
 * the explicit local development auth bypass, matching backend policy.
 */
import { supabase } from './supabaseClient';
import { API_URL } from '../config';
import { isDevAuthBypassEnabled } from './devAuth';

type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = Record<string, JsonValue>;

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const isFormDataBody = (body: BodyInit | null | undefined): body is FormData => (
  typeof FormData !== 'undefined' && body instanceof FormData
);

const resolveApiUrl = (endpoint: string): string => (
  /^https?:\/\//i.test(endpoint) ? endpoint : `${API_URL}${endpoint}`
);

const toEndpointWithParams = (endpoint: string, params: URLSearchParams): string => {
  const query = params.toString();
  return query ? `${endpoint}?${query}` : endpoint;
};

const parseErrorPayload = async (response: Response): Promise<unknown> => {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json().catch(() => ({}));
  }
  return response.text().catch(() => '');
};

const errorMessageFromPayload = (payload: unknown, fallback: string): string => {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
  }

  if (typeof payload === 'string' && payload.trim()) {
    return payload;
  }

  return fallback;
};

const handleAuthFailure = async (): Promise<never> => {
  if (!isDevAuthBypassEnabled()) {
    await supabase.auth.signOut();
    window.location.href = '/login';
  }
  throw new ApiError('Session expired. Please login again.', 401);
};

export const getDevClientIdParam = (clientId?: string): URLSearchParams => {
  const params = new URLSearchParams();
  if (isDevAuthBypassEnabled() && clientId?.trim()) {
    params.set('client_id', clientId.trim());
  }
  return params;
};

/**
 * Get authentication headers with JWT token.
 */
export async function getAuthHeaders(): Promise<Record<string, string>> {
  if (isDevAuthBypassEnabled()) {
    return {};
  }

  const { data: { session } } = await supabase.auth.getSession();

  if (!session) {
    throw new ApiError('Not authenticated. Please login.', 401);
  }

  return {
    Authorization: `Bearer ${session.access_token}`,
  };
}

export async function apiFetch(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const authHeaders = await getAuthHeaders();
  const headers = new Headers(options.headers);

  Object.entries(authHeaders).forEach(([key, value]) => {
    headers.set(key, value);
  });

  if (options.body && !isFormDataBody(options.body) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(resolveApiUrl(endpoint), {
    ...options,
    headers,
  });

  if (response.status === 401) {
    await handleAuthFailure();
  }

  return response;
}

/**
 * Make an authenticated API request and parse its JSON response.
 */
export async function apiRequest<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  try {
    const response = await apiFetch(endpoint, options);

    if (!response.ok) {
      const errorData = await parseErrorPayload(response);
      throw new ApiError(
        errorMessageFromPayload(errorData, response.statusText),
        response.status,
        errorData
      );
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return await response.json() as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error('API request failed:', error);
    throw new ApiError('Network error. Please try again.', 0);
  }
}

/**
 * Upload form data with authentication.
 */
export async function uploadFile<T = unknown>(
  endpoint: string,
  formData: FormData
): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'POST',
    body: formData,
  });
}

export async function fetchAuthenticatedBlobUrl(endpoint: string): Promise<string> {
  const response = await apiFetch(endpoint);
  if (!response.ok) {
    const errorData = await parseErrorPayload(response);
    throw new ApiError(
      errorMessageFromPayload(errorData, response.statusText),
      response.status,
      errorData
    );
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

// =============================================================================
// Convenience methods for common operations
// =============================================================================

export async function getAllDocuments<T = unknown>() {
  return apiRequest<T>('/api/documents');
}

export async function getSortedDocuments<T = unknown>() {
  return getAllDocuments<T>();
}

export async function getDocument<T = unknown>(documentId: string) {
  return apiRequest<T>(`/api/documents/${encodeURIComponent(documentId)}`);
}

export async function uploadDocument<T = unknown>(
  file: File,
  clientId?: string,
  persona?: string,
  job?: string
) {
  const formData = new FormData();
  formData.append('file', file);
  if (persona) formData.append('persona', persona);
  if (job) formData.append('job', job);

  const params = getDevClientIdParam(clientId);
  return uploadFile<T>(toEndpointWithParams('/upload/active_file', params), formData);
}

export async function uploadContextFiles<T = unknown>(
  files: File[],
  clientId?: string,
  persona?: string,
  job?: string,
  considerPrevious?: boolean
) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  if (persona) formData.append('persona', persona);
  if (job) formData.append('job', job);
  if (considerPrevious !== undefined) {
    formData.append('consider_previous', String(considerPrevious));
  }

  const params = getDevClientIdParam(clientId);
  return uploadFile<T>(toEndpointWithParams('/upload/context_files', params), formData);
}

export async function deleteDocument(documentId: string, permanent = false) {
  return apiRequest(`/api/documents/${encodeURIComponent(documentId)}?permanent=${permanent}`, {
    method: 'DELETE',
  });
}

export async function deleteAllDocuments(documentIds: string[], permanent = false) {
  await Promise.all(documentIds.map((documentId) => deleteDocument(documentId, permanent)));
  return { success: true, count: documentIds.length };
}

export async function updateDocumentMetadata(
  documentId: string,
  metadata: Record<string, unknown>
) {
  return apiRequest(`/api/documents/${encodeURIComponent(documentId)}/update-metadata`, {
    method: 'POST',
    body: JSON.stringify(metadata),
  });
}

export async function getRecommendations(
  documentId: string,
  page = 1,
  persona?: string,
  job?: string,
  includeCrossDocument = true
) {
  const params = new URLSearchParams({
    page: String(page),
    include_cross_document: String(includeCrossDocument),
  });

  if (persona) params.append('persona', persona);
  if (job) params.append('job', job);

  return apiRequest(`/api/recommendations/${encodeURIComponent(documentId)}?${params}`);
}

export async function getInsights(
  documentId: string,
  page = 1,
  persona?: string,
  job?: string
) {
  const params = new URLSearchParams({ page: String(page) });

  if (persona) params.append('persona', persona);
  if (job) params.append('job', job);

  return apiRequest(`/api/insights/${encodeURIComponent(documentId)}?${params}`);
}

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

export async function analyzeTextSelection(
  selectedText: string,
  documentId: string,
  page: number,
  persona?: string,
  job?: string,
  includeCrossDocument = true
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

export async function askGeminiSelection(
  documentId: string,
  selectedText: string,
  page: number,
  contextChars = 500
) {
  return apiRequest('/api/ask-gemini-selection', {
    method: 'POST',
    body: JSON.stringify({
      document_id: documentId,
      selected_text: selectedText,
      page,
      context_chars: contextChars,
    }),
  });
}

export async function generateAudio(
  text: string,
  documentId?: string,
  page = 1
) {
  return apiRequest('/api/generate-podcast', {
    method: 'POST',
    body: JSON.stringify({
      selected_text: text,
      document_id: documentId,
      page,
    }),
  });
}

export async function generatePodcast(
  content: string | undefined,
  documentId: string,
  page = 1,
  persona?: string,
  job?: string,
  includeRelated = true
) {
  return apiRequest('/api/generate-podcast', {
    method: 'POST',
    body: JSON.stringify({
      content,
      selected_text: content,
      document_id: documentId,
      page,
      persona,
      job,
      include_related: includeRelated,
    }),
  });
}

export async function splitDocument(
  documentId: string,
  splits: Array<{ name: string; start_page: number; end_page: number }>
) {
  return apiRequest('/api/split-document', {
    method: 'POST',
    body: JSON.stringify({
      document_id: documentId,
      splits,
    }),
  });
}

export async function mergeDocuments(documentIds: string[], outputName: string) {
  return apiRequest('/api/merge-documents', {
    method: 'POST',
    body: JSON.stringify({
      document_ids: documentIds,
      output_name: outputName,
    }),
  });
}

// =============================================================================
// Public endpoints
// =============================================================================

export async function publicApiRequest<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  try {
    const headers = new Headers(options.headers);
    if (options.body && !isFormDataBody(options.body) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    const response = await fetch(resolveApiUrl(endpoint), {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await parseErrorPayload(response);
      throw new ApiError(
        errorMessageFromPayload(errorData, response.statusText),
        response.status,
        errorData
      );
    }

    return await response.json() as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    console.error('API request failed:', error);
    throw new ApiError('Network error. Please try again.', 0);
  }
}

export async function healthCheck() {
  return publicApiRequest('/health');
}

export async function getConfig() {
  return publicApiRequest('/config');
}
