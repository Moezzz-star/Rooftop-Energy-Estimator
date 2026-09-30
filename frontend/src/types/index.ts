/**
 * Shared TypeScript types. Domain DTO types are inferred from the Zod schemas
 * (single source of truth) and re-exported here so feature code can import
 * either from `@/schemas` or `@/types`.
 */
export type {
  User,
  TokenPair,
  AccessTokenResponse,
  LoginInput,
  RegisterInput,
  RegisterPayload,
  Project,
  ProjectList,
  CreateProjectInput,
  Analysis,
  AnalysisList,
  AnalysisArea,
  AnalysisStatus,
  AnalysisCreateInput,
  Job,
  JobStage,
  JobStatus,
  JobStageStatus,
  Building,
  BuildingList,
  BuildingDetail,
  RoofGeometry,
  SolarEstimate,
  ResultsSummary,
  Feature,
  FeatureCollection,
  Geometry,
  Point,
  Polygon,
  MultiPolygon,
} from '@/schemas';

export type { StageKey } from '@/schemas';
