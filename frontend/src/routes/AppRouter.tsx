import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '@/layout';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { ProtectedRoute } from './ProtectedRoute';
import { featureRoutes } from './featureRoutes';
import { ROUTES } from './paths';

/**
 * Router core. Public auth routes + a protected layout (AppShell) that hosts
 * the dashboard and all `featureRoutes`. Add screens via `featureRoutes` or by
 * replacing placeholder page bodies — avoid editing this file.
 */
export function AppRouter(): JSX.Element {
  return (
    <Routes>
      <Route path={ROUTES.login} element={<LoginPage />} />
      <Route path={ROUTES.register} element={<RegisterPage />} />

      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route path={ROUTES.dashboard} element={<DashboardPage />} />
        {featureRoutes.map((route) => (
          <Route key={route.path} path={route.path} element={route.element} />
        ))}
      </Route>

      <Route path="/" element={<Navigate to={ROUTES.dashboard} replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
