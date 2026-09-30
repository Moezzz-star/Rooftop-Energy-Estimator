import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AppThemeProvider } from '@/theme';
import { StatusChip } from './StatusChip';

describe('StatusChip', () => {
  const cases: { status: Parameters<typeof StatusChip>[0]['status']; label: string }[] = [
    { status: 'draft', label: 'Draft' },
    { status: 'running', label: 'Running' },
    { status: 'completed', label: 'Completed' },
    { status: 'failed', label: 'Failed' },
    { status: 'succeeded', label: 'Succeeded' },
  ];

  it.each(cases)('renders the "$label" label for status "$status"', ({ status, label }) => {
    render(
      <AppThemeProvider>
        <StatusChip status={status} />
      </AppThemeProvider>,
    );
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.getByLabelText(`Status: ${label}`)).toBeInTheDocument();
  });
});
