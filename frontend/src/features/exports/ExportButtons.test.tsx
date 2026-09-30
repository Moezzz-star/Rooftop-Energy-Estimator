import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/renderWithProviders';
import { ExportButtons } from './components/ExportButtons';

const ANALYSIS_ID = 'd3b07384-d9a7-4f9e-8b2a-1c2d3e4f5a6b';
const CSV_EXPORT_ID = '11111111-1111-1111-1111-111111111111';
const DOWNLOAD_URL = 'http://localhost:8000/media/exports/analysis.csv';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const PENDING = {
  id: CSV_EXPORT_ID,
  kind: 'csv',
  status: 'pending',
  checksum: null,
  bytes: null,
  created_at: '2026-01-15T10:00:00Z',
  download_url: null,
};

const READY = {
  ...PENDING,
  status: 'ready',
  checksum: 'abc123',
  bytes: 2048,
  download_url: DOWNLOAD_URL,
};

describe('ExportButtons', () => {
  let downloadFetched: string | null;

  beforeEach(() => {
    downloadFetched = null;
    Object.defineProperty(URL, 'createObjectURL', { writable: true, value: () => 'blob:mock' });
    Object.defineProperty(URL, 'revokeObjectURL', { writable: true, value: () => undefined });

    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url === DOWNLOAD_URL) {
          downloadFetched = url;
          return Promise.resolve(new Response('id,area\n1,500', { status: 200 }));
        }
        if (url.includes(`/analyses/${ANALYSIS_ID}/exports/`) && init?.method === 'POST') {
          return Promise.resolve(jsonResponse(PENDING, 202));
        }
        if (url.includes(`/exports/${CSV_EXPORT_ID}/`)) {
          return Promise.resolve(jsonResponse(READY));
        }
        return Promise.resolve(jsonResponse({ detail: 'not found' }, 404));
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders one button per export kind', () => {
    renderWithProviders(<ExportButtons analysisId={ANALYSIS_ID} />, { withAuth: false });
    expect(screen.getByRole('button', { name: /generate csv export/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate geojson export/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate pdf export/i })).toBeInTheDocument();
  });

  it('requests, polls to ready, then downloads via the authenticated URL', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ExportButtons analysisId={ANALYSIS_ID} />, { withAuth: false });

    await user.click(screen.getByRole('button', { name: /generate csv export/i }));

    const download = await screen.findByRole(
      'button',
      { name: /download csv export/i },
      { timeout: 4000 },
    );
    expect(download).toBeInTheDocument();

    await user.click(download);
    await waitFor(() => expect(downloadFetched).toBe(DOWNLOAD_URL));
  });
});
