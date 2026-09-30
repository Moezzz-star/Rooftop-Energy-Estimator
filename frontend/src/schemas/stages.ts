/**
 * Canonical pipeline stage machine keys (see code-architecture.md §7) mapped to
 * human-readable labels for the processing progress UI. The wizard/processing
 * engineer drives the progress bar off `/analyses/{id}/job/` stage names and
 * looks up display text here.
 */
export const STAGE_KEYS = [
  'VALIDATE_REQUEST',
  'READ_IMAGERY_METADATA',
  'NORMALIZE_IMAGERY',
  'SUPER_RESOLUTION',
  'READ_RASTER_WINDOWS',
  'TILE_IMAGERY',
  'PREPROCESS_TILES',
  'RUN_INFERENCE',
  'REASSEMBLE_PREDICTIONS',
  'THRESHOLD',
  'MORPHOLOGY_CLEANUP',
  'FILTER_COMPONENTS',
  'VECTORIZE',
  'REPAIR_GEOMETRY',
  'SIMPLIFY_POLYGONS',
  'CALCULATE_AREAS',
  'AGGREGATE_CONFIDENCE',
  'PERSIST_ARTIFACTS',
  'RUN_SOLAR_ESTIMATION',
  'PUBLISH_RESULTS',
] as const;

export type StageKey = (typeof STAGE_KEYS)[number];

export const STAGE_LABELS: Record<StageKey, string> = {
  VALIDATE_REQUEST: 'Validating request',
  READ_IMAGERY_METADATA: 'Reading imagery metadata',
  NORMALIZE_IMAGERY: 'Normalizing imagery',
  SUPER_RESOLUTION: 'Super-resolution enhancement',
  READ_RASTER_WINDOWS: 'Reading raster windows',
  TILE_IMAGERY: 'Tiling imagery',
  PREPROCESS_TILES: 'Preprocessing tiles',
  RUN_INFERENCE: 'Running building detection',
  REASSEMBLE_PREDICTIONS: 'Reassembling predictions',
  THRESHOLD: 'Thresholding mask',
  MORPHOLOGY_CLEANUP: 'Cleaning up mask',
  FILTER_COMPONENTS: 'Filtering small components',
  VECTORIZE: 'Vectorizing footprints',
  REPAIR_GEOMETRY: 'Repairing geometry',
  SIMPLIFY_POLYGONS: 'Simplifying polygons',
  CALCULATE_AREAS: 'Calculating areas',
  AGGREGATE_CONFIDENCE: 'Aggregating confidence',
  PERSIST_ARTIFACTS: 'Persisting artifacts',
  RUN_SOLAR_ESTIMATION: 'Estimating solar potential',
  PUBLISH_RESULTS: 'Publishing results',
};

/** Resolve a stage label with a sensible fallback for unknown keys. */
export function stageLabel(key: string): string {
  return (STAGE_LABELS as Record<string, string>)[key] ?? key;
}
