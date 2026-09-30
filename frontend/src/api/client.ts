import { authBridge } from './authBridge';
import { ApiError, toApiError } from './errors';

export const API_BASE_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export type QueryParams = Record<string, string | number | boolean | undefined | null>;

export interface RequestOptions {
  /** Query string parameters (undefined/null values are skipped). */
  params?: QueryParams;
  /** JSON-serializable request body. Ignored when `formData` is set. */
  body?: unknown;
  /** Multipart body for file uploads (e.g. imagery). */
  formData?: FormData;
  /** Extra headers merged onto the defaults. */
  headers?: Record<string, string>;
  /** AbortSignal for cancellation (wired by TanStack Query). */
  signal?: AbortSignal;
  /** Skip Authorization header + refresh retry (auth endpoints). */
  skipAuth?: boolean;
}

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

function buildUrl(path: string, params?: QueryParams): string {
  const base = API_BASE_URL.replace(/\/$/, '');
  const suffix = path.startsWith('/') ? path : `/${path}`;
  const url = new URL(`${base}${suffix}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function parseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return null;
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function execute(method: Method, url: string, options: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json', ...options.headers };

  let payload: BodyInit | undefined;
  if (options.formData) {
    payload = options.formData; // browser sets multipart boundary
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(options.body);
  }

  if (!options.skipAuth) {
    const token = authBridge.getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const init: RequestInit = { method, headers };
  if (payload !== undefined) init.body = payload;
  if (options.signal) init.signal = options.signal;

  return fetch(url, init);
}

/**
 * Core request. Injects the JWT access token, and on a 401 attempts a single
 * token refresh via the auth bridge before retrying once. Non-2xx responses are
 * parsed through the error envelope and thrown as `ApiError`.
 */
async function request(method: Method, path: string, options: RequestOptions = {}): Promise<unknown> {
  const url = buildUrl(path, options.params);

  let response: Response;
  try {
    response = await execute(method, url, options);
  } catch {
    throw toApiError(null, 0);
  }

  if (response.status === 401 && !options.skipAuth) {
    const newToken = await authBridge.refresh();
    if (newToken) {
      try {
        response = await execute(method, url, options);
      } catch {
        throw toApiError(null, 0);
      }
    }
  }

  const parsed = await parseBody(response);
  if (!response.ok) {
    throw toApiError(parsed, response.status);
  }
  return parsed;
}

export const http = {
  get: (path: string, options?: RequestOptions): Promise<unknown> => request('GET', path, options),
  post: (path: string, options?: RequestOptions): Promise<unknown> =>
    request('POST', path, options),
  patch: (path: string, options?: RequestOptions): Promise<unknown> =>
    request('PATCH', path, options),
  put: (path: string, options?: RequestOptions): Promise<unknown> => request('PUT', path, options),
  delete: (path: string, options?: RequestOptions): Promise<unknown> =>
    request('DELETE', path, options),
};

export { ApiError };
