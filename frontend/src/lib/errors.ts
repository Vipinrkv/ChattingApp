export type AppErrorSource = 'api' | 'auth' | 'network' | 'timeout' | 'ui' | 'unknown';

export class AppError extends Error {
  code: string;
  status?: number;
  source: AppErrorSource;
  details?: unknown;

  constructor(
    message: string,
    options: {
      code?: string;
      status?: number;
      source?: AppErrorSource;
      details?: unknown;
    } = {},
  ) {
    super(message);
    this.name = 'AppError';
    this.code = options.code ?? 'error';
    this.status = options.status;
    this.source = options.source ?? 'unknown';
    this.details = options.details;
  }
}

export function parseApiError(payload: any, fallback: string, status?: number) {
  const errorPayload = payload?.error;
  const message = errorPayload?.message || payload?.detail || payload?.message || fallback;
  const code = errorPayload?.code || payload?.code || statusToCode(status);
  return new AppError(message, {
    code,
    status,
    source: status === 0 ? 'network' : 'api',
    details: errorPayload?.details || payload?.details,
  });
}

export function normalizeError(error: unknown, fallback = 'Something went wrong.') {
  if (error instanceof AppError) return error;
  if (error instanceof Error) {
    return new AppError(error.message || fallback, {
      code: error.name === 'AbortError' ? 'request_timeout' : 'error',
      source: error.name === 'AbortError' ? 'timeout' : 'unknown',
    });
  }
  return new AppError(fallback, { code: 'error', source: 'unknown' });
}

function statusToCode(status?: number) {
  if (!status) return 'request_failed';
  if (status === 401) return 'unauthorized';
  if (status === 403) return 'forbidden';
  if (status === 404) return 'not_found';
  if (status === 408) return 'request_timeout';
  if (status === 409) return 'conflict';
  if (status === 422) return 'validation_failed';
  if (status === 429) return 'rate_limited';
  if (status >= 500) return 'server_error';
  return 'request_failed';
}
