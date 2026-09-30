import type { ReactElement, ReactNode } from 'react';
import { render, type RenderResult } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { createQueryClient } from '@/api';
import { AppThemeProvider } from '@/theme';
import { AuthProvider } from '@/hooks';

export interface RenderOptions {
  /** Initial router entries for MemoryRouter. */
  route?: string;
  /** Wrap with the real AuthProvider (default true). */
  withAuth?: boolean;
}

/**
 * Render a component tree with the app's providers (QueryClient, theme, auth,
 * router). Each call gets a fresh QueryClient so tests stay isolated.
 */
export function renderWithProviders(ui: ReactElement, options: RenderOptions = {}): RenderResult {
  const { route = '/', withAuth = true } = options;
  const queryClient = createQueryClient();

  const Auth = ({ children }: { children: ReactNode }): JSX.Element =>
    withAuth ? <AuthProvider>{children}</AuthProvider> : <>{children}</>;

  return render(
    <QueryClientProvider client={queryClient}>
      <AppThemeProvider>
        <Auth>
          <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
        </Auth>
      </AppThemeProvider>
    </QueryClientProvider>,
  );
}
