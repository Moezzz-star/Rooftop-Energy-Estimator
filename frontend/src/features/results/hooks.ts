import { useApiQuery, queryKeys } from '@/api';
import type { FeatureCollection } from '@/schemas';
import type { BBox } from '@/maps';
import { resultsApi, type ListBuildingsParams } from './api';
import type { BuildingList, BuildingDetail, ResultsSummaryDetail } from './schemas';

/** Query: aggregated results summary. */
export function useResultsSummary(analysisId: string | undefined) {
  return useApiQuery<ResultsSummaryDetail>({
    queryKey: queryKeys.analyses.results(analysisId ?? 'none'),
    queryFn: (signal) => resultsApi.summary(analysisId as string, signal),
    enabled: Boolean(analysisId),
  });
}

/** Query: paginated buildings list. */
export function useBuildings(analysisId: string | undefined, params: ListBuildingsParams = {}) {
  return useApiQuery<BuildingList>({
    queryKey: queryKeys.analyses.buildings(analysisId ?? 'none', { ...params } as Record<string, unknown>),
    queryFn: (signal) => resultsApi.listBuildings(analysisId as string, params, signal),
    enabled: Boolean(analysisId),
  });
}

/** Query: full building detail (roof + solar). */
export function useBuildingDetail(buildingId: string | null) {
  return useApiQuery<BuildingDetail>({
    queryKey: queryKeys.buildings.detail(buildingId ?? 'none'),
    queryFn: (signal) => resultsApi.buildingDetail(buildingId as string, signal),
    enabled: Boolean(buildingId),
  });
}

/** Query: map-ready roof polygons for the given bbox/zoom. */
export function useMapFeatures(
  analysisId: string | undefined,
  bbox: BBox | null,
  zoom: number,
) {
  return useApiQuery<FeatureCollection>({
    queryKey: queryKeys.analyses.features(analysisId ?? 'none', {
      bbox: bbox ? bbox.join(',') : null,
      zoom,
    }),
    queryFn: (signal) => resultsApi.features(analysisId as string, bbox as BBox, zoom, signal),
    enabled: Boolean(analysisId) && bbox !== null,
    staleTime: 60_000,
  });
}
