import { z } from 'zod';
import { polygonSchema, resultsSummarySchema, type pointSchema, paginatedSchema } from '@/schemas';

/**
 * Feature-local schemas matching the live geospatial responses. These differ
 * from the shared building DTO: the backend emits `centroid_lon`/`centroid_lat`
 * (not a `centroid` Point) and a `solar_estimates` array (not a single `solar`).
 */

export const buildingRowSchema = z.object({
  id: z.string().uuid(),
  index: z.number().int().nonnegative(),
  area_m2: z.number().nonnegative(),
  confidence: z.number().min(0).max(1),
  centroid_lon: z.number().nullable().default(null),
  centroid_lat: z.number().nullable().default(null),
  geometry: polygonSchema.nullable().default(null),
  // Optional per-building solar metrics. Present only if the list endpoint
  // includes them; used for client-side distribution charts. Never invented.
  annual_kwh: z.number().nonnegative().optional(),
  capacity_kwp: z.number().nonnegative().optional(),
  specific_yield: z.number().nonnegative().optional(),
});
export type BuildingRow = z.infer<typeof buildingRowSchema>;

/**
 * §16 DataQualityService output, exposed on the results summary when the
 * backend provides it. This is a transparency indicator, NOT a calibrated
 * confidence score.
 */
export const dataQualityFactorSchema = z.object({
  label: z.string(),
  detail: z.string().optional(),
  impact: z.enum(['positive', 'neutral', 'negative']).optional(),
});
export type DataQualityFactor = z.infer<typeof dataQualityFactorSchema>;

export const dataQualitySchema = z.object({
  indicator: z.string(),
  factors: z.array(dataQualityFactorSchema).default([]),
  notes: z.array(z.string()).default([]),
});
export type DataQuality = z.infer<typeof dataQualitySchema>;

/**
 * Results summary extended with optional totals/averages and the §16 data
 * quality block. Extends the shared summary schema so the required fields stay
 * in sync; extra backend fields are captured here without touching global schemas.
 */
export const resultsSummaryDetailSchema = resultsSummarySchema.extend({
  total_usable_area_m2: z.number().nonnegative().optional(),
  average_annual_kwh: z.number().nonnegative().optional(),
  average_area_m2: z.number().nonnegative().optional(),
  average_specific_yield: z.number().nonnegative().optional(),
  data_quality: dataQualitySchema.nullable().optional(),
});
export type ResultsSummaryDetail = z.infer<typeof resultsSummaryDetailSchema>;

export const buildingListSchema = paginatedSchema(buildingRowSchema);
export type BuildingList = z.infer<typeof buildingListSchema>;

export const roofDetailSchema = z.object({
  id: z.union([z.string(), z.number()]).optional(),
  tilt_deg: z.number(),
  azimuth_deg: z.number(),
  usable_area_m2: z.number().nonnegative(),
  source: z.string().optional(),
});
export type RoofDetail = z.infer<typeof roofDetailSchema>;

export const solarEstimateRowSchema = z.object({
  id: z.union([z.string(), z.number()]).optional(),
  capacity_kwp: z.number().nonnegative(),
  annual_kwh: z.number().nonnegative(),
  specific_yield: z.number().nonnegative(),
  usable_area_m2: z.number().nonnegative(),
  monthly_kwh: z.array(z.number()),
  disclaimer: z.string(),
});
export type SolarEstimateRow = z.infer<typeof solarEstimateRowSchema>;

export const buildingDetailSchema = buildingRowSchema.extend({
  geometry: polygonSchema,
  roof: roofDetailSchema.nullable().default(null),
  solar_estimates: z.array(solarEstimateRowSchema).default([]),
  // Building-level data-quality warnings (§16). Used for transparency when the
  // summary has no aggregate data-quality block.
  warnings: z.array(z.string()).default([]),
});
export type BuildingDetail = z.infer<typeof buildingDetailSchema>;

/** The centroid as a GeoJSON Point (derived from lon/lat) for convenience. */
export function centroidPoint(row: BuildingRow): z.infer<typeof pointSchema> | null {
  if (row.centroid_lon === null || row.centroid_lat === null) return null;
  return { type: 'Point', coordinates: [row.centroid_lon, row.centroid_lat] };
}
