import { stageLabel } from '@/schemas';

/**
 * Display labels for the ten durable pipeline stage machine keys emitted by the
 * backend for this slice (lowercase keys — the shared `STAGE_LABELS` map keys
 * the granular §7 pipeline with UPPERCASE keys, so it does not cover these).
 */
const SLICE_STAGE_LABELS: Record<string, string> = {
  validate_request: 'Validate request',
  load_imagery: 'Load imagery',
  validate_raster: 'Validate raster',
  tile: 'Tile imagery',
  segment: 'Segment (building detection)',
  postprocess_mask: 'Post-process mask',
  extract_polygons: 'Extract polygons',
  solar_calc: 'Solar calculation',
  persist_results: 'Persist results',
  prepare_report: 'Prepare report',
};

/** Title-case a snake/kebab-case machine key as a readable fallback label. */
export function humanizeStageKey(key: string): string {
  return key
    .replace(/[_-]+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

/**
 * Resolve a stage label with a robust fallback chain:
 *   1. this slice's 10-stage label map,
 *   2. the shared `stageLabel` lookup (granular §7 keys),
 *   3. a humanized version of the raw machine key.
 *
 * The UI is always driven off the polled stage names — never a hardcoded list —
 * so unknown keys still render a sensible label.
 */
export function formatStageLabel(name: string): string {
  const slice = SLICE_STAGE_LABELS[name];
  if (slice) return slice;
  const shared = stageLabel(name);
  if (shared !== name) return shared;
  return humanizeStageKey(name);
}
