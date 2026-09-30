import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { Link, Typography } from '@mui/material';
import { AuthLayout } from '@/layout';
import { RegisterForm } from '@/features/auth';
import { ROUTES } from '@/routes/paths';

export function RegisterPage(): JSX.Element {
  const navigate = useNavigate();

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Start estimating rooftop solar potential"
      footer={
        <Typography variant="body2" color="text.secondary">
          Already have an account?{' '}
          <Link component={RouterLink} to={ROUTES.login}>
            Sign in
          </Link>
        </Typography>
      }
    >
      <RegisterForm onSuccess={() => navigate(ROUTES.dashboard, { replace: true })} />
    </AuthLayout>
  );
}
