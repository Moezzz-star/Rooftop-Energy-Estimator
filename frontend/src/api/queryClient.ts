import { QueryClient } from '@tanstack/react-query';
import { ApiError } from './errors';

/**
 * Shared QueryClient. Auth failures are not retried (the client already handles
 * a single refresh+retry); other errors get one retry.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
            return false;
          }
          return failureCount < 1;
        },
      },
      mutations: {
        retry: false,
      },
    },
  });
}
