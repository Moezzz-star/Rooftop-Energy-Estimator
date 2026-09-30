import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/renderWithProviders';

vi.mock('@/features/map', () => ({
  RoofMap: () => <div data-testid="roof-map" />,
}));

import { ResultsView } from './components/ResultsView';

const ANALYSIS_ID = 'd3b07384-d9a7-4f9e-8b2a-1c2d3e4f5a6b';
const BUILDING_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
const DISCLAIMER =
  'These are engineering estimates for indicative purposes only and are not a bankable photovoltaic yield study.';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const ANALYSIS_DETAIL = {
  id: ANALYSIS_ID,
  name: 'Sample rooftop analysis',
  status: 'completed',
  project: '3f2504e0-4f89-41d3-9a0c-0305e82c3301',
  created_at: '2026-01-15T10:00:00Z',
  submitted_at: '2026-01-15T10:01:00Z',
  completed_at: '2026-01-15T10:05:00Z',
  areas: [
    {
      id: 1,
      label: 'sample analysis area',
      area: {
        type: 'Polygon',
        coordinates: [
          [
            [9.0, 48.7507],
            [9.0035, 48.7507],
            [9.0035, 48.753],
            [9.0, 48.753],
            [9.0, 48.7507],
          ],
        ],
      },
    },
  ],
};

const SUMMARY = {
  building_count: 1,
  total_area_m2: 1234,
  total_usable_area_m2: 900,
  total_capacity_kwp: 12.5,
  total_annual_kwh: 15000,
  disclaimer: DISCLAIMER,
};

const BUILDING_LIST = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: BUILDING_ID,
      index: 1,
      area_m2: 500,
      confidence: 0.92,
      centroid_lon: 9.0017,
      centroid_lat: 48.7518,
      geometry: null,
    },
  ],
};

const BUILDING_DETAIL = {
  id: BUILDING_ID,
  index: 1,
  area_m2: 500,
  confidence: 0.92,
  centroid_lon: 9.0017,
  centroid_lat: 48.7518,
  geometry: {
    type: 'Polygon',
    coordinates: [
      [
        [9.0, 48.7507],
        [9.0035, 48.7507],
        [9.0035, 48.753],
        [9.0, 48.7507],
      ],
    ],
  },
  roof: { id: 1, tilt_deg: 30, azimuth_deg: 180, usable_area_m2: 400, source: 'default' },
  solar_estimates: [
    {
      id: 1,
      capacity_kwp: 8,
      annual_kwh: 9000,
      specific_yield: 1125,
      usable_area_m2: 400,
      monthly_kwh: [400, 500, 700, 800, 900, 1000, 1050, 980, 820, 640, 450, 360],
      disclaimer: DISCLAIMER,
    },
  ],
};

describe('ResultsView', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes(`/buildings/${BUILDING_ID}/`)) return Promise.resolve(jsonResponse(BUILDING_DETAIL));
        if (url.includes(`/analyses/${ANALYSIS_ID}/results/`)) return Promise.resolve(jsonResponse(SUMMARY));
        if (url.includes(`/analyses/${ANALYSIS_ID}/buildings/`)) return Promise.resolve(jsonResponse(BUILDING_LIST));
        if (url.includes(`/analyses/${ANALYSIS_ID}/features/`))
          return Promise.resolve(jsonResponse({ type: 'FeatureCollection', features: [] }));
        if (url.includes(`/analyses/${ANALYSIS_ID}/`)) return Promise.resolve(jsonResponse(ANALYSIS_DETAIL));
        return Promise.resolve(jsonResponse({ detail: 'not found' }, 404));
      }),
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  it('renders the zone summary, disclaimer and a building detail with a monthly chart', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ResultsView analysisId={ANALYSIS_ID} />, { withAuth: false });

    // Zone summary (labels are locale-independent; numbers are localized).
    expect(await screen.findByText('Buildings detected')).toBeInTheDocument();
    expect(screen.getByText('Total capacity')).toBeInTheDocument();
    expect(screen.getByText(/kWp/)).toBeInTheDocument();

    // Mandatory DEC-02 disclaimer.
    expect(screen.getAllByText(DISCLAIMER).length).toBeGreaterThanOrEqual(1);

    // Open building detail.
    const viewButton = await screen.findByRole('button', {
      name: /view details for building 1/i,
    });
    await user.click(viewButton);

    const drawer = await screen.findByRole('presentation');
    await waitFor(() => {
      expect(within(drawer).getByText('Monthly energy estimate')).toBeInTheDocument();
    });
    expect(within(drawer).getByText('30°')).toBeInTheDocument();
    expect(within(drawer).getByText('Capacity')).toBeInTheDocument();
    expect(
      within(drawer).getByText('Estimated monthly energy in kilowatt-hours'),
    ).toBeInTheDocument();
  });
});
