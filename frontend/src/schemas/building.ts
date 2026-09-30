import { z } from 'zod';
import { pointSchema, polygonSchema } from './geojson';
import { paginatedSchema } from './project';

/** Tabular building row from GET /analyses/{id}/buildings/ (geometry omitted by default). */
export const buildingSchema = z.object({
  id: z.string().uuid(),
  index: z.number().int().nonnegative(),
  area_m2: z.number().nonnegative(),
  confidence: z.number().min(0).max(1),
  centroid: pointSchema,
});

export const buildingListSchema = paginatedSchema(buildingSchema);

export const roofGeometrySchema = z.object({
  tilt_deg: z.number(),
  azimuth_deg: z.number(),
  usable_area_m2: z.number().nonnegative(),
  source: z.string(),
  geometry: polygonSchema.nullable().default(null),
});

/** 12 monthly kWh values, Jan..Dec. */
export const monthlyKwhSchema = z.array(z.number().nonnegative()).length(12);

export const solarEstimateSchema = z.object({
  capacity_kwp: z.number().nonnegative(),
  annual_kwh: z.number().nonnegative(),
  monthly_kwh: monthlyKwhSchema,
  specific_yield: z.number().nonnegative(),
  usable_area_m2: z.number().nonnegative(),
  disclaimer: z.string(),
});

/** Full detail from GET /buildings/{id}/. */
export const buildingDetailSchema = buildingSchema.extend({
  geometry: polygonSchema,
  roof: roofGeometrySchema.nullable().default(null),
  solar: solarEstimateSchema.nullable().default(null),
});

export type Building = z.infer<typeof buildingSchema>;
export type BuildingList = z.infer<typeof buildingListSchema>;
export type RoofGeometry = z.infer<typeof roofGeometrySchema>;
export type SolarEstimate = z.infer<typeof solarEstimateSchema>;
export type BuildingDetail = z.infer<typeof buildingDetailSchema>;
