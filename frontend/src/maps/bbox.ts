/**
 * MapLibre / bbox helpers. The `/analyses/{id}/features/` endpoint requires a
 * `bbox` and a zoom-dependent `simplify` tolerance (code-architecture.md §4,
 * row 19 — unbounded GeoJSON is rejected). These pure helpers are consumed by
 * the map/results feature; MapLibre setup (style, layers, draw controls) will
 * be added alongside them.
 */

/** Geographic bounding box as [minLon, minLat, maxLon, maxLat] (EPSG:4326). */
export type BBox = readonly [number, number, number, number];

/**
 * Compute the bounding box of nested GeoJSON coordinate arrays (rings of a
 * Polygon or MultiPolygon). Pure/recursive so it works for any nesting depth.
 * Returns `null` when no coordinates are present.
 */
export function coordinatesBBox(coordinates: unknown): BBox | null {
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;

  const visit = (node: unknown): void => {
    if (!Array.isArray(node)) return;
    const lon = node[0];
    const lat = node[1];
    if (typeof lon === 'number' && typeof lat === 'number') {
      if (lon < minLon) minLon = lon;
      if (lat < minLat) minLat = lat;
      if (lon > maxLon) maxLon = lon;
      if (lat > maxLat) maxLat = lat;
      return;
    }
    for (const child of node) visit(child);
  };

  visit(coordinates);
  if (!Number.isFinite(minLon) || !Number.isFinite(minLat)) return null;
  return [minLon, minLat, maxLon, maxLat];
}

/**
 * Compute the bbox of a GeoJSON Polygon/MultiPolygon-like geometry object.
 * Returns `null` when the geometry has no usable coordinates.
 */
export function geometryBBox(geometry: { coordinates?: unknown } | null | undefined): BBox | null {
  if (!geometry || geometry.coordinates === undefined) return null;
  return coordinatesBBox(geometry.coordinates);
}

/** Expand a bbox outward by a fractional padding of its span (min 1e-4 deg). */
export function padBBox(bbox: BBox, fraction = 0.05): BBox {
  const [minLon, minLat, maxLon, maxLat] = bbox;
  const padLon = Math.max((maxLon - minLon) * fraction, 1e-4);
  const padLat = Math.max((maxLat - minLat) * fraction, 1e-4);
  return [minLon - padLon, minLat - padLat, maxLon + padLon, maxLat + padLat];
}

/** Serialize a bbox for the `bbox` query parameter (comma-separated). */
export function serializeBBox(bbox: BBox): string {
  return bbox.join(',');
}

/** Parse a comma-separated bbox string; returns null if malformed. */
export function parseBBox(value: string): BBox | null {
  const parts = value.split(',').map(Number);
  if (parts.length !== 4 || parts.some((n) => Number.isNaN(n))) return null;
  return [parts[0]!, parts[1]!, parts[2]!, parts[3]!] as BBox;
}

/**
 * Map a map zoom level to a geometry simplification tolerance in meters.
 * Lower zoom (further out) -> coarser simplification. Bounded to keep the
 * server-side `ST_SimplifyPreserveTopology` request reasonable.
 */
export function zoomToSimplifyMeters(zoom: number): number {
  if (zoom >= 18) return 0.25;
  if (zoom >= 16) return 0.5;
  if (zoom >= 14) return 1;
  if (zoom >= 12) return 2.5;
  if (zoom >= 10) return 5;
  return 10;
}
