/**
 * Public API layer surface. Feature `api.ts` modules import the `http` client,
 * `parseResponse`, error types and query key/hook helpers from here.
 */
export { http, API_BASE_URL } from './client';
export type { RequestOptions, QueryParams } from './client';
export { ApiError, toApiError, errorEnvelopeSchema } from './errors';
export type { ErrorEnvelope } from './errors';
export { authBridge } from './authBridge';
export { createQueryClient } from './queryClient';
export { useApiQuery, useApiMutation, parseResponse } from './hooks';
export { queryKeys } from './queryKeys';
