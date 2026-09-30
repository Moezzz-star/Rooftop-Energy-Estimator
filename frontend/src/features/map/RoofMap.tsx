import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import maplibregl, { type GeoJSONSource, type MapGeoJSONFeature } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Box } from '@mui/material';
import type { FeatureCollection } from '@/schemas';
import type { BBox } from '@/maps';
import { MapControls } from './components/MapControls';
import {
  OFFLINE_MAP_STYLE,
  ROOF_SOURCE_ID,
  ROOF_FILL_LAYER_ID,
  ROOF_LINE_LAYER_ID,
  ROOF_HIGHLIGHT_LAYER_ID,
  ROOF_THEMATIC_LAYER_ID,
  BUILDING_ID_PROPERTY,
  availableSolarMetrics,
  metricDomain,
  solarFillColorExpression,
  type FillMode,
  type SolarMetricKey,
} from './mapStyle';

export interface RoofMapProps {
  /** Roof polygons to render (null while loading). */
  features: FeatureCollection | null;
  /** Bounding box the map fits to on load ([minLon, minLat, maxLon, maxLat]). */
  bounds: BBox | null;
  /** Currently selected building id (highlighted), if any. */
  selectedId?: string | null;
  /** Called with a building id when a roof polygon is clicked. */
  onSelectBuilding?: (buildingId: string) => void;
  /** Accessible label for the map region. */
  ariaLabel?: string;
}

const EMPTY_COLLECTION: FeatureCollection = { type: 'FeatureCollection', features: [] };
const DEFAULT_OPACITY = 0.35;

/** The GeoJSON payload type accepted by a MapLibre GeoJSON source. */
type MapData = Parameters<GeoJSONSource['setData']>[0];

/** Bridge our Zod-inferred FeatureCollection to MapLibre's GeoJSON typing. */
function toMapData(collection: FeatureCollection): MapData {
  return collection as unknown as MapData;
}

/** Copy each feature's top-level id into a property for stable identification. */
function withIdProperty(collection: FeatureCollection): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: collection.features.map((feature) => ({
      ...feature,
      properties: {
        ...(feature.properties ?? {}),
        [BUILDING_ID_PROPERTY]: feature.id !== undefined ? String(feature.id) : null,
      },
    })),
  };
}

/**
 * MapLibre GL map that renders roof polygons over a blank offline style. All
 * MapLibre access is isolated here so it can be mocked in jsdom tests (MapLibre
 * does not run under jsdom). Adds a solar-thematic fill layer, layer/opacity
 * controls, a legend, a scale control and a fit-to-bounds button.
 */
export function RoofMap({
  features,
  bounds,
  selectedId = null,
  onSelectBuilding,
  ariaLabel = 'Roof polygons map',
}: RoofMapProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const loadedRef = useRef(false);
  const onSelectRef = useRef(onSelectBuilding);
  onSelectRef.current = onSelectBuilding;

  const [fillMode, setFillMode] = useState<FillMode>('polygons');
  const [opacity, setOpacity] = useState<number>(DEFAULT_OPACITY);

  const availableMetrics = useMemo(() => availableSolarMetrics(features), [features]);
  const [metric, setMetric] = useState<SolarMetricKey>('annual_kwh');

  // Keep the selected metric valid as the available set changes.
  useEffect(() => {
    if (availableMetrics.length === 0) return;
    if (!availableMetrics.some((item) => item.key === metric)) {
      setMetric(availableMetrics[0]!.key);
    }
  }, [availableMetrics, metric]);

  // Fall back to plain polygons if the thematic metric disappears from the data.
  useEffect(() => {
    if (fillMode === 'thematic' && availableMetrics.length === 0) setFillMode('polygons');
  }, [fillMode, availableMetrics]);

  const domain = useMemo(() => metricDomain(features, metric), [features, metric]);

  const fitBounds = useCallback((): void => {
    const map = mapRef.current;
    if (!map || !bounds) return;
    map.fitBounds(
      [
        [bounds[0], bounds[1]],
        [bounds[2], bounds[3]],
      ],
      { padding: 40, duration: 0 },
    );
  }, [bounds]);

  // Create the map once.
  useEffect(() => {
    if (!containerRef.current) return undefined;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: OFFLINE_MAP_STYLE,
      center: [0, 0],
      zoom: 1,
      attributionControl: false,
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left');

    map.on('load', () => {
      map.addSource(ROOF_SOURCE_ID, { type: 'geojson', data: toMapData(EMPTY_COLLECTION) });
      map.addLayer({
        id: ROOF_FILL_LAYER_ID,
        type: 'fill',
        source: ROOF_SOURCE_ID,
        paint: { 'fill-color': '#1f6feb', 'fill-opacity': DEFAULT_OPACITY },
      });
      map.addLayer({
        id: ROOF_THEMATIC_LAYER_ID,
        type: 'fill',
        source: ROOF_SOURCE_ID,
        layout: { visibility: 'none' },
        paint: { 'fill-color': '#1f6feb', 'fill-opacity': DEFAULT_OPACITY },
      });
      map.addLayer({
        id: ROOF_LINE_LAYER_ID,
        type: 'line',
        source: ROOF_SOURCE_ID,
        paint: { 'line-color': '#1f6feb', 'line-width': 1 },
      });
      map.addLayer({
        id: ROOF_HIGHLIGHT_LAYER_ID,
        type: 'line',
        source: ROOF_SOURCE_ID,
        paint: { 'line-color': '#d29922', 'line-width': 3 },
        filter: ['==', ['get', BUILDING_ID_PROPERTY], '__none__'],
      });
      loadedRef.current = true;

      const handleClick = (
        event: maplibregl.MapLayerMouseEvent & { features?: MapGeoJSONFeature[] },
      ): void => {
        const feature = event.features?.[0];
        const id = feature?.properties?.[BUILDING_ID_PROPERTY];
        if (typeof id === 'string' && id.length > 0) onSelectRef.current?.(id);
      };
      map.on('click', ROOF_FILL_LAYER_ID, handleClick);
      map.on('click', ROOF_THEMATIC_LAYER_ID, handleClick);
      map.on('mouseenter', ROOF_FILL_LAYER_ID, () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', ROOF_FILL_LAYER_ID, () => {
        map.getCanvas().style.cursor = '';
      });
    });

    return () => {
      loadedRef.current = false;
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Push feature data + fit bounds whenever they change.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = (): void => {
      const source = map.getSource(ROOF_SOURCE_ID) as GeoJSONSource | undefined;
      if (source) source.setData(toMapData(withIdProperty(features ?? EMPTY_COLLECTION)));
      if (bounds) {
        map.fitBounds(
          [
            [bounds[0], bounds[1]],
            [bounds[2], bounds[3]],
          ],
          { padding: 40, duration: 0 },
        );
      }
    };
    if (loadedRef.current) apply();
    else map.once('load', apply);
  }, [features, bounds]);

  // Update the highlight filter when the selection changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = (): void => {
      if (!map.getLayer(ROOF_HIGHLIGHT_LAYER_ID)) return;
      map.setFilter(ROOF_HIGHLIGHT_LAYER_ID, [
        '==',
        ['get', BUILDING_ID_PROPERTY],
        selectedId ?? '__none__',
      ]);
    };
    if (loadedRef.current) apply();
    else map.once('load', apply);
  }, [selectedId]);

  // Apply fill-mode visibility, opacity and the thematic colour ramp.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = (): void => {
      if (!map.getLayer(ROOF_FILL_LAYER_ID) || !map.getLayer(ROOF_THEMATIC_LAYER_ID)) return;
      const thematicActive = fillMode === 'thematic' && domain !== null;
      map.setLayoutProperty(ROOF_FILL_LAYER_ID, 'visibility', thematicActive ? 'none' : 'visible');
      map.setLayoutProperty(
        ROOF_THEMATIC_LAYER_ID,
        'visibility',
        thematicActive ? 'visible' : 'none',
      );
      map.setPaintProperty(ROOF_FILL_LAYER_ID, 'fill-opacity', opacity);
      map.setPaintProperty(ROOF_THEMATIC_LAYER_ID, 'fill-opacity', opacity);
      if (thematicActive && domain) {
        map.setPaintProperty(
          ROOF_THEMATIC_LAYER_ID,
          'fill-color',
          solarFillColorExpression(metric, domain),
        );
      }
    };
    if (loadedRef.current) apply();
    else map.once('load', apply);
  }, [fillMode, opacity, metric, domain]);

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '100%', minHeight: 320 }}>
      <MapControls
        fillMode={fillMode}
        onFillModeChange={setFillMode}
        availableMetrics={availableMetrics}
        metric={metric}
        onMetricChange={setMetric}
        domain={domain}
        opacity={opacity}
        onOpacityChange={setOpacity}
        onFitBounds={fitBounds}
        canFit={bounds !== null}
      />
      <Box
        ref={containerRef}
        role="region"
        aria-label={ariaLabel}
        sx={{ width: '100%', height: '100%', minHeight: 320, borderRadius: 1, overflow: 'hidden' }}
      />
    </Box>
  );
}
