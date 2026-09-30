import { useState } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { createQueryClient } from '@/api';
import { AppThemeProvider } from '@/theme';
import { AuthProvider } from '@/hooks';
import { AppRouter } from '@/routes';

/**
 * Root provider composition:
 * QueryClient -> Theme -> Auth (needs QueryClient) -> Router -> routes.
 */
export function App(): JSX.Element {
  const [queryClient] = useState(() => createQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <AppThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <AppRouter />
          </BrowserRouter>
        </AuthProvider>
      </AppThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
