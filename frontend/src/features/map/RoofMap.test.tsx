import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/renderWithProviders';
import type { FeatureCollection } from '@/schemas';

/**
 * Fake MapLibre map: MapLibre GL cannot run under jsdom, so we mock the module
 * and record the paint/layout/filter calls RoofMap makes. `load` fires
 * synchronously so the layer setup runs during render. Defined via vi.hoisted
 * so it is available when the (hoisted) vi.mock factory runs.
 */
const h = vi.hoisted(() => {
  const paintCalls: Array<{ layer: string; name: string; value: unknown }> = [];
  const layoutCalls: Array<{ layer: string; name: string; value: unknown }> = [];
  const addedLayers: string[] = [];
  const state = { fitBoundsCount: 0 };

  class FakeMap {
    addControl(): void {}
    on(event: string, ...rest: unknown[]): void {
      const handler = rest[rest.length - 1];
      if (event === 'load' && typeof handler === 'function') (handler as () => void)();
    }
    once(event: string, handler: () => void): void {
      if (event === 'load') handler();
    }
    addSource(): void {}
    addLayer(layer: { id: string }): void {
      addedLayers.push(layer.id);
    }
    getLayer(id: string): { id: string } | undefined {
      return addedLayers.includes(id) ? { id } : undefined;
    }
    getSource(): { setData: () => void } {
      return { setData: () => undefined };
    }
    setPaintProperty(layer: string, name: string, value: unknown): void {
      paintCalls.push({ layer, name, value });
    }
    setLayoutProperty(layer: string, name: string, value: unknown): void {
      layoutCalls.push({ layer, name, value });
    }
    setFilter(): void {}
    fitBounds(): void {
      state.fitBoundsCount += 1;
    }
    getCanvas(): { style: Record<string, string> } {
      return { style: {} };
    }
    remove(): void {}
  }

  return { paintCalls, layoutCalls, addedLayers, state, FakeMap };
});

vi.mock('maplibre-gl', () => ({
  default: {
    Map: h.FakeMap,
    NavigationControl: class {},
    ScaleControl: class {},
  },
}));

import { RoofMap } from './RoofMap';
import { ROOF_THEMATIC_LAYER_ID } from './mapStyle';

const THEMATIC: FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      id: 'b1',
      geometry: { type: 'Polygon', coordinates: [[[0, 0], [0, 1], [1, 1], [0, 0]]] },
      properties: { annual_kwh: 100, capacity_kwp: 5 },
    },
    {
      type: 'Feature',
      id: 'b2',
      geometry: { type: 'Polygon', coordinates: [[[2, 2], [2, 3], [3, 3], [2, 2]]] },
      properties: { annual_kwh: 900, capacity_kwp: 20 },
    },
  ],
};

const PLAIN: FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      id: 'b1',
      geometry: { type: 'Polygon', coordinates: [[[0, 0], [0, 1], [1, 1], [0, 0]]] },
      properties: {},
    },
  ],
};

describe('RoofMap controls', () => {
  beforeEach(() => {
    h.paintCalls.length = 0;
    h.layoutCalls.length = 0;
    h.addedLayers.length = 0;
    h.state.fitBoundsCount = 0;
  });

  it('disables the solar thematic toggle when no metric is present', () => {
    renderWithProviders(<RoofMap features={PLAIN} bounds={null} />, { withAuth: false });
    expect(screen.getByRole('button', { name: /solar thematic/i })).toBeDisabled();
  });

  it('enables thematic mode and applies a data-driven fill when metrics exist', async () => {
    const user = userEvent.setup();
    renderWithProviders(<RoofMap features={THEMATIC} bounds={[0, 0, 3, 3]} />, {
      withAuth: false,
    });

    const solar = screen.getByRole('button', { name: /solar thematic/i });
    expect(solar).toBeEnabled();
    await user.click(solar);

    expect(
      h.layoutCalls.some(
        (call) => call.layer === ROOF_THEMATIC_LAYER_ID && call.value === 'visible',
      ),
    ).toBe(true);
    expect(
      h.paintCalls.some(
        (call) => call.layer === ROOF_THEMATIC_LAYER_ID && call.name === 'fill-color',
      ),
    ).toBe(true);

    expect(screen.getAllByText(/Annual energy \(kWh\)/).length).toBeGreaterThanOrEqual(1);
  });

  it('applies an explicit fill-opacity paint value', () => {
    renderWithProviders(<RoofMap features={PLAIN} bounds={null} />, { withAuth: false });
    expect(screen.getByLabelText('Roof opacity')).toBeInTheDocument();
    expect(h.paintCalls.some((call) => call.name === 'fill-opacity')).toBe(true);
  });

  it('offers a fit-to-bounds button that recentres the map', async () => {
    const user = userEvent.setup();
    renderWithProviders(<RoofMap features={PLAIN} bounds={[0, 0, 1, 1]} />, { withAuth: false });
    const before = h.state.fitBoundsCount;
    await user.click(screen.getByRole('button', { name: /fit map to analysis area/i }));
    expect(h.state.fitBoundsCount).toBeGreaterThan(before);
  });
});
