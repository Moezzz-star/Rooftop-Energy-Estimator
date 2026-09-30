import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/test/renderWithProviders';
import { ProcessingView } from './components/ProcessingView';

const ANALYSIS_ID = 'd3b07384-d9a7-4f9e-8b2a-1c2d3e4f5a6b';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const JOB_RESPONSE = {
  id: '11111111-1111-1111-1111-111111111111',
  analysis_id: ANALYSIS_ID,
  status: 'running',
  cancel_requested: false,
  queued_at: '2026-01-15T10:00:00Z',
  started_at: '2026-01-15T10:00:01Z',
  finished_at: null,
  error: null,
  stages: [
    { name: 'validate_request', sequence: 1, status: 'succeeded', started_at: null, finished_at: null, duration_ms: 42, detail: null },
    { name: 'segment', sequence: 5, status: 'running', started_at: null, finished_at: null, duration_ms: null, detail: null },
    // Unknown machine key — must be humanized, never dropped.
    { name: 'quantum_flux_align', sequence: 9, status: 'pending', started_at: null, finished_at: null, duration_ms: null, detail: null },
  ],
};

describe('ProcessingView', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes(`/analyses/${ANALYSIS_ID}/job/`)) {
          return Promise.resolve(jsonResponse(JOB_RESPONSE));
        }
        return Promise.resolve(jsonResponse({ detail: 'not found' }, 404));
      }),
    );
  });
  afterEach(() => vi.unstubAllGlobals());

  it('renders stages driven by the polled job, humanizing unknown keys', async () => {
    renderWithProviders(<ProcessingView analysisId={ANALYSIS_ID} />, { withAuth: false });

    // Known slice keys get friendly labels.
    expect(await screen.findByText('Validate request')).toBeInTheDocument();
    expect(screen.getByText('Segment (building detection)')).toBeInTheDocument();
    // Unknown key is humanized (underscores -> spaces, title-cased).
    expect(screen.getByText('Quantum Flux Align')).toBeInTheDocument();

    // Overall status chip reflects the polled status (also appears per-stage).
    expect(screen.getAllByLabelText('Status: Running').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Overall status:')).toBeInTheDocument();

    // Per-stage duration surfaces for completed stages.
    expect(screen.getByText(/Took 42 ms/)).toBeInTheDocument();

    // Active job exposes a cancel affordance.
    expect(screen.getByRole('button', { name: /cancel processing/i })).toBeInTheDocument();
  });
});
