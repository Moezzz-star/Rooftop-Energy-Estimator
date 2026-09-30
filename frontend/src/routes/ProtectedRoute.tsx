import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { LoadingState } from '@/components';
import { useAuth } from '@/hooks';
import { ROUTES } from './paths';

/**
 * Gates authenticated routes. While the session is being restored it shows a
 * loader; once resolved it redirects unauthenticated users to /login,
 * preserving the attempted location for post-login return.
 */
export function ProtectedRoute({ children }: { children: ReactNode }): JSX.Element {
  const { isAuthenticated, isBootstrapping } = useAuth();
  const location = useLocation();

  if (isBootstrapping) {
    return <LoadingState label="Restoring your session…" minHeight="60vh" />;
  }

  if (!isAuthenticated) {
    return <Navigate to={ROUTES.login} replace state={{ from: location }} />;
  }

  return <>{children}</>;
}
