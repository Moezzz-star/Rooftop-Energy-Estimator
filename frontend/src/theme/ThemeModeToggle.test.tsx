import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppThemeProvider, ThemeModeToggle, useThemeMode, THEME_MODE_STORAGE_KEY } from './index';

function ModeProbe(): JSX.Element {
  const { resolvedMode, mode } = useThemeMode();
  return (
    <div>
      <span data-testid="resolved">{resolvedMode}</span>
      <span data-testid="mode">{mode}</span>
    </div>
  );
}

describe('theme mode toggle', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('defaults to system (resolved light in tests) and switches to dark', async () => {
    const user = userEvent.setup();
    render(
      <AppThemeProvider>
        <ThemeModeToggle />
        <ModeProbe />
      </AppThemeProvider>,
    );

    expect(screen.getByTestId('mode').textContent).toBe('system');
    expect(screen.getByTestId('resolved').textContent).toBe('light');

    await user.click(screen.getByRole('button', { name: /change theme/i }));
    await user.click(screen.getByRole('menuitem', { name: /dark/i }));

    expect(screen.getByTestId('resolved').textContent).toBe('dark');
    expect(screen.getByTestId('mode').textContent).toBe('dark');
    expect(window.localStorage.getItem(THEME_MODE_STORAGE_KEY)).toBe('dark');
  });
});
