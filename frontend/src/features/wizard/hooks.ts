import { useApiQuery } from '@/api';
import { imageryApi, type ImagerySource } from './imageryApi';

/** Query: available imagery provider sources. */
export function useImagerySources() {
  return useApiQuery<ImagerySource[]>({
    queryKey: ['imagery', 'sources'],
    queryFn: (signal) => imageryApi.listSources(signal),
    staleTime: 5 * 60_000,
  });
}
