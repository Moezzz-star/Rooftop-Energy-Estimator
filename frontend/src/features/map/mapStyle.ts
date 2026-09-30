import type { ExpressionSpecification, StyleSpecification } from 'maplibre-gl';
import type { FeatureCollection } from '@/schemas';

/**
 * A minimal, fully offline MapLibre style: a single solid background layer with
 * no external tile/basemap/glyph/sprite dependencies. This keeps the results
 * map deterministic and network-free — roof polygons are added as a runtime
 * GeoJSON source/layers on top of this background.
 */
export const OFFLINE_MAP_STYLE: StyleSpecification = {
  version: 8,
  name: 'offline-blank',
  sources: {},
  layers: [
    {
      id: 'background',
      type: 'background',
      paint: {
        'background-color': '#e9edf2',
      },
    },
  ],
};

export const ROOF_SOURCE_ID = 'roofs';
export const ROOF_FILL_LAYER_ID = 'roofs-fill';
export const ROOF_LINE_LAYER_ID = 'roofs-line';
export const ROOF_HIGHLIGHT_LAYER_ID = 'roofs-highlight';
/** Data-driven fill layer that colours roofs by a solar metric. */
export const ROOF_THEMATIC_LAYER_ID = 'roofs-thematic';

/** Property key we copy the feature id into for click/highlight identification. */
export const BUILDING_ID_PROPERTY = '__buildingId';

/** Which fill layer is currently active. */
export type FillMode = 'polygons' | 'thematic';

/** Solar metric keys the thematic layer can colour by (must exist on feature properties). */
export type SolarMetricKey = 'annual_kwh' | 'capacity_kwp';

export interface SolarMetricConfig {
  readonly key: SolarMetricKey;
  readonly label: string;
  readonly unit: string;
}

/** Metrics the thematic layer understands, in display order. */
export const SOLAR_METRICS: readonly SolarMetricConfig[] = [
  { key: 'annual_kwh', label: 'Annual energy', unit: 'kWh' },
  { key: 'capacity_kwp', label: 'Capacity', unit: 'kWp' },
];

/** Sequential low→high colour ramp (ColorBrewer OrRd, colour-blind safe enough for a legend). */
export const SOLAR_RAMP: readonly string[] = [
  '#fef0d9',
  '#fdcc8a',
  '#fc8d59',
  '#e34a33',
  '#b30000',
];

/** Read a numeric feature property, returning null when absent/non-finite. */
function readNumericProperty(
  properties: Record<string, unknown> | null | undefined,
  key: string,
): number | null {
  const value = properties?.[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/**
 * Determine which solar metrics are actually carried by the feature properties.
 * The thematic mode is only offered for metrics present in the data — we never
 * invent values the backend did not send.
 */
export function availableSolarMetrics(collection: FeatureCollection | null): SolarMetricConfig[] {
  if (!collection) return [];
  const present = new Set<SolarMetricKey>();
  for (const feature of collection.features) {
    for (const metric of SOLAR_METRICS) {
      if (readNumericProperty(feature.properties, metric.key) !== null) present.add(metric.key);
    }
  }
  return SOLAR_METRICS.filter((metric) => present.has(metric.key));
}

/** Min/max of a metric across the features; null when the metric is absent. */
export function metricDomain(
  collection: FeatureCollection | null,
  metric: SolarMetricKey,
): [number, number] | null {
  if (!collection) return null;
  let min = Infinity;
  let max = -Infinity;
  for (const feature of collection.features) {
    const value = readNumericProperty(feature.properties, metric);
    if (value === null) continue;
    if (value < min) min = value;
    if (value > max) max = value;
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) return null;
  return [min, max];
}

/**
 * Build a MapLibre `interpolate` expression that maps a metric value to the
 * colour ramp across the supplied [min, max] domain. Degenerate domains (a
 * single distinct value) are widened by 1 so the interpolation stays valid.
 */
export function solarFillColorExpression(
  metric: SolarMetricKey,
  domain: [number, number],
): ExpressionSpecification {
  const [rawMin, rawMax] = domain;
  const min = rawMin;
  const max = rawMax > rawMin ? rawMax : rawMin + 1;
  const stops: Array<number | string> = [];
  const last = SOLAR_RAMP.length - 1;
  SOLAR_RAMP.forEach((color, index) => {
    const t = last === 0 ? 0 : index / last;
    stops.push(min + (max - min) * t, color);
  });
  return [
    'interpolate',
    ['linear'],
    ['coalesce', ['to-number', ['get', metric]], min],
    ...stops,
  ] as unknown as ExpressionSpecification;
}
