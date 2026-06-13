//src/lib/api.ts
import { auth } from '../firebase';
import { AppError, parseApiError } from './errors';
import { queueRequest } from './offlineQueue';

const defaultApiBase = typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : 'http://localhost:8000';

function resolveApiBase(): string {
  const envApiBase = import.meta.env.VITE_API_BASE;
  const envApiUrl = import.meta.env.VITE_API_URL;

  // Prioritize VITE_API_URL if it points to a remote server (e.g. Render backend)
  if (envApiUrl && !envApiUrl.includes('localhost') && !envApiUrl.includes('127.0.0.1') && !envApiUrl.includes('::1')) {
    return envApiUrl;
  }

  if (envApiBase) {
    // If VITE_API_BASE is a remote server, use it
    if (!envApiBase.includes('localhost') && !envApiBase.includes('127.0.0.1') && !envApiBase.includes('::1')) {
      return envApiBase;
    }

    // If it's a localhost URL, check if the app itself is running on localhost
    if (typeof window !== 'undefined') {
      const currentHost = window.location.hostname;
      const isPageLocalhost = ['localhost', '127.0.0.1', '::1'].includes(currentHost);
      if (isPageLocalhost) {
        return envApiBase;
      }
    }
  }

  // Fallback to VITE_API_URL if VITE_API_BASE was a localhost proxy that we bypassed
  if (envApiUrl) {
    return envApiUrl;
  }

  return defaultApiBase;
}

const API_BASE = resolveApiBase();
if (typeof window !== 'undefined') {
  console.debug('[ChattingApp] API_BASE resolved to:', API_BASE);
}
const DEFAULT_TIMEOUT_MS = 12000;
const RETRY_STATUSES = new Set([408, 429, 500, 502, 503, 504]);

type ApiRequestOptions = RequestInit & {
  logoutOnAuthError?: boolean;
  skipOfflineQueue?: boolean;
};

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function getAuthToken(): Promise<string | null> {
  const storedToken = localStorage.getItem('authToken');

  if (!auth?.currentUser) {
    return storedToken;
  }

  try {
    const freshToken = await auth.currentUser.getIdToken();
    if (freshToken) {
      localStorage.setItem('authToken', freshToken);
      return freshToken;
    }
  } catch {
    return storedToken;
  }

  return storedToken;
}

let refreshPromise: Promise<boolean> | null = null;

async function attemptTokenRefresh(): Promise<boolean> {
  try {
    if (refreshPromise) {
      return await refreshPromise;
    }

    refreshPromise = (async () => {
      try {
        if (!auth || !auth.currentUser) return false;
        const idToken = await auth.currentUser.getIdToken(true);
        localStorage.setItem('authToken', idToken);
        return true;
      } catch {
        return false;
      }
    })();

    const result = await refreshPromise;
    refreshPromise = null;
    return result;
  } catch {
    refreshPromise = null;
    return false;
  }
}

function headersToRecord(headers: HeadersInit | undefined): Record<string, string> {
  if (!headers) return {};
  if (headers instanceof Headers) return Object.fromEntries(headers.entries());
  if (Array.isArray(headers)) return Object.fromEntries(headers);
  return headers as Record<string, string>;
}

function isMissingProfileMessage(message: string) {
  return message.toLowerCase().includes('profile not found');
}

export async function apiRequest(path: string, options: ApiRequestOptions = {}) {
  const { logoutOnAuthError = true, skipOfflineQueue = false, ...requestOptions } = options;
  let authToken = await getAuthToken();
  const method = requestOptions.method ?? 'GET';
  const maxAttempts = method === 'GET' ? 3 : 1;
  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

    try {
      const optionHeaders = headersToRecord(requestOptions.headers);
      const headers: Record<string, string> = {
        Accept: 'application/json',
        ...optionHeaders,
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      };

      if (requestOptions.body && !(requestOptions.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
      }

      const response = await fetch(`${API_BASE}${path}`, {
        ...requestOptions,
        signal: controller.signal,
        headers,
      });

      const contentType = response.headers.get('content-type');
      const payload = contentType?.includes('application/json') ? await response.json() : null;

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          const apiError = parseApiError(payload, response.statusText || 'Unauthorized', response.status);
          const message = apiError.message;

          if (response.status === 401 && isMissingProfileMessage(message)) {
            throw apiError;
          }

          const refreshed = await attemptTokenRefresh();
          if (refreshed) {
            authToken = await getAuthToken();
            await delay(1200);
            const retryResponse = await fetch(`${API_BASE}${path}`, {
              ...requestOptions,
              signal: controller.signal,
              headers: {
                Accept: 'application/json',
                ...optionHeaders,
                ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
                ...(requestOptions.body && !(requestOptions.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
              },
            });

            const retryContentType = retryResponse.headers.get('content-type');
            const retryPayload = retryContentType?.includes('application/json') ? await retryResponse.json() : null;
            if (retryResponse.ok) return retryPayload;

            const retryError = parseApiError(retryPayload, retryResponse.statusText || 'Unauthorized', retryResponse.status);
            const retryMessage = retryError.message;
            if (retryResponse.status === 401 && isMissingProfileMessage(retryMessage)) {
              throw retryError;
            }
          }

          if (logoutOnAuthError) {
            try {
              window.dispatchEvent(new CustomEvent('auth:logout'));
            } catch {
              // ignore
            }
          }

          throw apiError;
        }

        const apiError = parseApiError(payload, response.statusText || 'Request failed', response.status);
        const shouldRetry = attempt < maxAttempts && RETRY_STATUSES.has(response.status);
        if (shouldRetry) {
          await delay(250 * attempt);
          continue;
        }
        throw apiError;
      }

      return payload;
    } catch (err) {
      lastError = err instanceof Error ? err : new Error('Request failed');
      const isAbort = lastError.name === 'AbortError';
      const canQueueOfflineWrite =
        !skipOfflineQueue &&
        method !== 'GET' &&
        (isAbort || lastError.message === 'Failed to fetch' || !navigator.onLine);
      if (canQueueOfflineWrite) {
        const body = typeof requestOptions.body === 'string' ? requestOptions.body : undefined;
        const queued = await queueRequest({ path, method, body });
        return { queued: true, id: queued.id };
      }
      const canRetry = attempt < maxAttempts && (isAbort || lastError.message === 'Failed to fetch');
      if (!canRetry) {
        throw isAbort ? new AppError('Request timed out', { code: 'request_timeout', source: 'timeout' }) : lastError;
      }
      await delay(250 * attempt);
    } finally {
      window.clearTimeout(timeoutId);
    }
  }

  throw lastError ?? new AppError('Request failed', { code: 'request_failed', source: 'unknown' });
}

export function apiGet(path: string) {
  return apiRequest(path, { method: 'GET' });
}

export function apiGetWithoutAuthLogout(path: string) {
  return apiRequest(path, { method: 'GET', logoutOnAuthError: false });
}

export function apiPost(path: string, body: Record<string, unknown>) {
  return apiRequest(path, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function apiPut(path: string, body: Record<string, unknown>) {
  return apiRequest(path, {
    method: 'PUT',
    body: JSON.stringify(body),
  });
}

export function apiPostWithoutAuthLogout(path: string, body: Record<string, unknown>) {
  return apiRequest(path, {
    method: 'POST',
    body: JSON.stringify(body),
    logoutOnAuthError: false,
  });
}

export function apiPatch(path: string, body?: Record<string, unknown>) {
  return apiRequest(path, {
    method: 'PATCH',
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
}

export function apiPostForm(path: string, body: FormData) {
  return apiRequest(path, {
    method: 'POST',
    body,
  });
}

export function apiDelete(path: string) {
  return apiRequest(path, { method: 'DELETE' });
}
