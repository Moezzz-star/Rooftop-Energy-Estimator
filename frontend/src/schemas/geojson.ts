import { z } from 'zod';

/**
 * Minimal GeoJSON schemas (RFC 7946) covering the geometry types the
 * backend emits for analysis areas, building footprints and centroids.
 * Kept intentionally small — extend if the API starts returning more types.
 */

const positionSchema = z.array(z.number()); // [lon, lat] (+ optional altitude)

export const pointSchema = z.object({
  type: z.literal('Point'),
  coordinates: positionSchema,
});

export const polygonSchema = z.object({
  type: z.literal('Polygon'),
  coordinates: z.array(z.array(positionSchema)),
});

export const multiPolygonSchema = z.object({
  type: z.literal('MultiPolygon'),
  coordinates: z.array(z.array(z.array(positionSchema))),
});

export const geometrySchema = z.discriminatedUnion('type', [
  pointSchema,
  polygonSchema,
  multiPolygonSchema,
]);

export const featureSchema = z.object({
  type: z.literal('Feature'),
  geometry: geometrySchema,
  properties: z.record(z.string(), z.unknown()).nullable(),
  id: z.union([z.string(), z.number()]).optional(),
});

export const featureCollectionSchema = z.object({
  type: z.literal('FeatureCollection'),
  features: z.array(featureSchema),
  bbox: z.array(z.number()).optional(),
});

export type Point = z.infer<typeof pointSchema>;
export type Polygon = z.infer<typeof polygonSchema>;
export type MultiPolygon = z.infer<typeof multiPolygonSchema>;
export type Geometry = z.infer<typeof geometrySchema>;
export type Feature = z.infer<typeof featureSchema>;
export type FeatureCollection = z.infer<typeof featureCollectionSchema>;
