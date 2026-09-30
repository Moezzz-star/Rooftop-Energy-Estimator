import {
  useQuery,
  useMutation,
  type UseQueryResult,
  type UseMutationResult,
  type QueryKey,
} from '@tanstack/react-query';
import type { z } from 'zod';
import { ApiError } from './errors';

/**
 * Validate an unknown API payload against a Zod schema, converting schema
 * mismatches into an ApiError so the UI error path stays uniform.
 */
export function parseResponse<TSchema extends z.ZodTypeAny>(
  schema: TSchema,
  data: unknown,
): z.infer<TSchema> {
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new ApiError({
      code: 'response_validation_error',
      message: 'The server returned data in an unexpected format.',
      status: 0,
      details: result.error.flatten(),
    });
  }
  return result.data;
}

/**
 * Typed query wrapper. `fetcher` receives the request signal so the underlying
 * HTTP call can be aborted; errors are always `ApiError`.
 */
export function useApiQuery<TData>(options: {
  queryKey: QueryKey;
  queryFn: (signal: AbortSignal) => Promise<TData>;
  enabled?: boolean;
  staleTime?: number;
  refetchInterval?: number | false;
}): UseQueryResult<TData, ApiError> {
  return useQuery<TData, ApiError>({
    queryKey: options.queryKey,
    queryFn: ({ signal }) => options.queryFn(signal),
    ...(options.enabled !== undefined ? { enabled: options.enabled } : {}),
    ...(options.staleTime !== undefined ? { staleTime: options.staleTime } : {}),
    ...(options.refetchInterval !== undefined ? { refetchInterval: options.refetchInterval } : {}),
  });
}

/** Typed mutation wrapper; errors are always `ApiError`. */
export function useApiMutation<TData, TVariables>(options: {
  mutationFn: (variables: TVariables) => Promise<TData>;
  onSuccess?: (data: TData, variables: TVariables) => void | Promise<unknown>;
  onError?: (error: ApiError, variables: TVariables) => void;
}): UseMutationResult<TData, ApiError, TVariables> {
  return useMutation<TData, ApiError, TVariables>({
    mutationFn: options.mutationFn,
    ...(options.onSuccess ? { onSuccess: options.onSuccess } : {}),
    ...(options.onError ? { onError: options.onError } : {}),
  });
}
