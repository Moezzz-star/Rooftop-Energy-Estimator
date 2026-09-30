import { http, parseResponse, type QueryParams } from '@/api';
import { featureCollectionSchema, type FeatureCollection } from '@/schemas';
import { serializeBBox, zoomToSimplifyMeters, type BBox } from '@/maps';
import {
  buildingListSchema,
  buildingDetailSchema,
  resultsSummaryDetailSchema,
  type BuildingList,
  type BuildingDetail,
  type ResultsSummaryDetail,
} from './schemas';

export interface ListBuildingsParams {
  page?: number;
  min_area?: number;
  confidence?: number;
  order?: string;
}

/** Results, buildings and map-feature calls (code-architecture §4 #16-#19). */
export const resultsApi = {
  async summary(analysisId: string, signal?: AbortSignal): Promise<ResultsSummaryDetail> {
    const data = await http.get(`/analyses/${analysisId}/results/`, {
      ...(signal ? { signal } : {}),
    });
    return parseResponse(resultsSummaryDetailSchema, data);
  },

  async listBuildings(
    analysisId: string,
    params: ListBuildingsParams = {},
    signal?: AbortSignal,
  ): Promise<BuildingList> {
    const query: QueryParams = {};
    if (params.page !== undefined) query.page = params.page;
    if (params.min_area !== undefined) query.min_area = params.min_area;
    if (params.confidence !== undefined) query.confidence = params.confidence;
    if (params.order !== undefined) query.order = params.order;
    const data = await http.get(`/analyses/${analysisId}/buildings/`, {
      params: query,
      ...(signal ? { signal } : {}),
    });
    return parseResponse(buildingListSchema, data);
  },

  async buildingDetail(buildingId: string, signal?: AbortSignal): Promise<BuildingDetail> {
    const data = await http.get(`/buildings/${buildingId}/`, {
      ...(signal ? { signal } : {}),
    });
    return parseResponse(buildingDetailSchema, data);
  },

  async features(
    analysisId: string,
    bbox: BBox,
    zoom: number,
    signal?: AbortSignal,
  ): Promise<FeatureCollection> {
    const query: QueryParams = {
      bbox: serializeBBox(bbox),
      zoom,
      simplify: zoomToSimplifyMeters(zoom),
    };
    const data = await http.get(`/analyses/${analysisId}/features/`, {
      params: query,
      ...(signal ? { signal } : {}),
    });
    return parseResponse(featureCollectionSchema, data);
  },
};
