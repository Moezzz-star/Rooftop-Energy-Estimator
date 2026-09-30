import { useQuery, type QueryKey, type UseQueryResult } from '@tanstack/react-query';
import type { ApiError } from '@/api';

export interface UsePollingOptions<TData> {
  queryKey: QueryKey;
  queryFn: (signal: AbortSignal) => Promise<TData>;
  /** Returns true once the resource reaches a terminal state; polling stops. */
  isTerminal: (data: TData) => boolean;
  /** Poll interval in ms while non-terminal (default 2500). */
  intervalMs?: number;
  enabled?: boolean;
}

/**
 * Interval polling helper (used for job status via `/analyses/{id}/job/`).
 * Uses TanStack Query's function-form `refetchInterval` so polling stops as
 * soon as `isTerminal(data)` is satisfied.
 */
export function usePolling<TData>(
  options: UsePollingOptions<TData>,
): UseQueryResult<TData, ApiError> {
  const { queryKey, queryFn, isTerminal, intervalMs = 2500, enabled = true } = options;

  return useQuery<TData, ApiError>({
    queryKey,
    queryFn: ({ signal }) => queryFn(signal),
    enabled,
    staleTime: 0,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data !== undefined && isTerminal(data)) return false;
      return intervalMs;
    },
  });
}
