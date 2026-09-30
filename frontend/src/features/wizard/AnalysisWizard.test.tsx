import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/renderWithProviders';

// MapLibre does not run under jsdom — stub the map component.
vi.mock('@/features/map', () => ({
  RoofMap: () => <div data-testid="roof-map" />,
}));

import { AnalysisWizard } from './AnalysisWizard';

const PROJECT_ID = '3f2504e0-4f89-41d3-9a0c-0305e82c3301';
const ANALYSIS_ID = 'd3b07384-d9a7-4f9e-8b2a-1c2d3e4f5a6b';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

interface FetchCall {
  url: string;
  init: RequestInit | undefined;
}

let calls: FetchCall[];

function installFetch(): void {
  calls = [];
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, init });
    const method = (init?.method ?? 'GET').toUpperCase();

    if (url.includes('/projects/') && url.includes('/analyses/') && method === 'POST') {
      return Promise.resolve(
        jsonResponse(
          {
            id: ANALYSIS_ID,
            name: 'Sample rooftop analysis',
            status: 'draft',
            project: PROJECT_ID,
            created_at: '2026-01-15T10:00:00Z',
            submitted_at: null,
            completed_at: null,
            areas: [],
          },
          201,
        ),
      );
    }
    if (url.includes(`/analyses/${ANALYSIS_ID}/submit/`) && method === 'POST') {
      return Promise.resolve(
        jsonResponse(
          { analysis: { id: ANALYSIS_ID, status: 'queued' }, job: { id: 'job-1', status: 'queued' } },
          202,
        ),
      );
    }
    if (url.includes('/projects/') && method === 'GET') {
      return Promise.resolve(
        jsonResponse({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: PROJECT_ID,
              name: 'Warehouse rooftops',
              description: null,
              is_archived: false,
              created_at: '2026-01-15T10:00:00Z',
              updated_at: '2026-01-15T10:00:00Z',
            },
          ],
        }),
      );
    }
    if (url.includes('/imagery/sources/') && method === 'GET') {
      return Promise.resolve(
        jsonResponse({
          sources: [
            {
              name: 'uploaded_raster',
              title: 'Uploaded raster',
              description: 'User-uploaded GeoTIFF imagery.',
              supports_upload: true,
              supports_windowed_read: true,
              requires_network: false,
              available: true,
            },
          ],
        }),
      );
    }
    return Promise.resolve(jsonResponse({ detail: 'not found' }, 404));
  });
  vi.stubGlobal('fetch', fetchMock);
}

async function advanceToStep(user: ReturnType<typeof userEvent.setup>, times: number): Promise<void> {
  for (let i = 0; i < times; i += 1) {
    await user.click(screen.getByRole('button', { name: /next/i }));
  }
}

describe('AnalysisWizard', () => {
  beforeEach(() => installFetch());
  afterEach(() => vi.unstubAllGlobals());

  it('creates then submits the analysis with an Idempotency-Key and completes the flow', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AnalysisWizard />, { route: '/analyses/new', withAuth: false });

    // Step 1: project preselected once the list loads.
    await screen.findByText('Warehouse rooftops');
    await advanceToStep(user, 2); // project -> area -> imagery

    // Step 3: imagery source preselected (bundled sample).
    await screen.findByText(/uploaded raster/i);
    await advanceToStep(user, 1); // imagery -> name & review

    // Step 4: submit.
    const submit = await screen.findByRole('button', { name: /submit analysis/i });
    await user.click(submit);

    await waitFor(() => {
      const submitCall = calls.find((call) => call.url.includes(`/analyses/${ANALYSIS_ID}/submit/`));
      expect(submitCall).toBeDefined();
    });

    const createCall = calls.find(
      (call) => call.url.includes('/analyses/') && (call.init?.method ?? '').toUpperCase() === 'POST' && call.url.includes('/projects/'),
    );
    expect(createCall).toBeDefined();

    const submitCall = calls.find((call) => call.url.includes(`/analyses/${ANALYSIS_ID}/submit/`))!;
    const headers = new Headers(submitCall.init?.headers);
    expect(headers.get('Idempotency-Key')).toBeTruthy();
  });

  it('shows a validation error when the analysis name is cleared', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AnalysisWizard />, { route: '/analyses/new', withAuth: false });

    await screen.findByText('Warehouse rooftops');
    await advanceToStep(user, 3); // reach name & review

    const nameField = await screen.findByLabelText(/analysis name/i);
    await user.clear(nameField);
    await user.click(screen.getByRole('button', { name: /submit analysis/i }));

    expect(await screen.findByText('Analysis name is required')).toBeInTheDocument();
  });
});
