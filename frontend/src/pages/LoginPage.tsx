import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import { Link, Typography } from '@mui/material';
import { AuthLayout } from '@/layout';
import { LoginForm } from '@/features/auth';
import { ROUTES } from '@/routes/paths';

interface LocationState {
  from?: { pathname?: string };
}

export function LoginPage(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState | null;
  const redirectTo = state?.from?.pathname ?? ROUTES.dashboard;

  return (
    <AuthLayout
      title="Rooftop Energy Estimator"
      subtitle="Sign in to estimate rooftop solar potential"
      footer={
        <Typography variant="body2" color="text.secondary">
          Need an account?{' '}
          <Link component={RouterLink} to={ROUTES.register}>
            Create one
          </Link>
        </Typography>
      }
    >
      <LoginForm onSuccess={() => navigate(redirectTo, { replace: true })} />
    </AuthLayout>
  );
}
