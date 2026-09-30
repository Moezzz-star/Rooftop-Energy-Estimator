import { z } from 'zod';
import { featureCollectionSchema, polygonSchema, multiPolygonSchema } from './geojson';
import { paginatedSchema } from './project';

export const analysisStatusSchema = z.enum([
  'draft',
  'queued',
  'running',
  'completed',
  'failed',
  'cancelled',
]);

export type AnalysisStatus = z.infer<typeof analysisStatusSchema>;

/** Analysis area geometry: a single polygon or multipolygon in EPSG:4326. */
export const analysisAreaSchema = z.union([polygonSchema, multiPolygonSchema]);

export const analysisSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  status: analysisStatusSchema,
  project: z.string().uuid(),
  area: analysisAreaSchema.nullable().default(null),
  created_at: z.string().datetime({ offset: true }),
  submitted_at: z.string().datetime({ offset: true }).nullable().default(null),
  completed_at: z.string().datetime({ offset: true }).nullable().default(null),
});

export const analysisListSchema = paginatedSchema(analysisSchema);

export const analysisCreateInputSchema = z.object({
  name: z
    .string()
    .min(1, 'Analysis name is required')
    .max(120, 'Analysis name must be 120 characters or fewer'),
  project: z.string().uuid('A project must be selected'),
  area: analysisAreaSchema,
});

/** Convenience alias for map-ready feature collections returned by /features/. */
export const analysisFeaturesSchema = featureCollectionSchema;

export type Analysis = z.infer<typeof analysisSchema>;
export type AnalysisList = z.infer<typeof analysisListSchema>;
export type AnalysisArea = z.infer<typeof analysisAreaSchema>;
export type AnalysisCreateInput = z.infer<typeof analysisCreateInputSchema>;
