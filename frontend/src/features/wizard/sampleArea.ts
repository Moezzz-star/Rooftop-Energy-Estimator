import rawSampleArea from '@/assets/sample_area.geojson?raw';
import { featureCollectionSchema, type AnalysisArea } from '@/schemas';
import { geometryBBox, padBBox, type BBox } from '@/maps';

/**
 * The bundled sample analysis area (Stuttgart rooftops), imported from the
 * committed GeoJSON asset, parsed and Zod-validated at module load. Used as the
 * default area for the sample-path wizard — no drawing/upload required.
 */
const collection = featureCollectionSchema.parse(JSON.parse(rawSampleArea));

const firstGeometry = collection.features[0]?.geometry;

if (!firstGeometry || (firstGeometry.type !== 'Polygon' && firstGeometry.type !== 'MultiPolygon')) {
  throw new Error('Bundled sample_area.geojson must contain a Polygon or MultiPolygon feature.');
}

export const SAMPLE_AREA: AnalysisArea = firstGeometry;

export const SAMPLE_AREA_LABEL: string =
  (collection.features[0]?.properties?.label as string | undefined) ?? 'Sample analysis area';

const rawBBox = geometryBBox(SAMPLE_AREA);

export const SAMPLE_AREA_BBOX: BBox = rawBBox ? padBBox(rawBBox) : [-180, -90, 180, 90];

/** GeoJSON FeatureCollection wrapper for rendering the sample area on a map. */
export const SAMPLE_AREA_FEATURE_COLLECTION = {
  type: 'FeatureCollection' as const,
  features: [
    {
      type: 'Feature' as const,
      geometry: SAMPLE_AREA,
      properties: { label: SAMPLE_AREA_LABEL },
    },
  ],
};
