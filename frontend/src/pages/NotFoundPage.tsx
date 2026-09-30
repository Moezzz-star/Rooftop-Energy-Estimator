import { Link as RouterLink } from 'react-router-dom';
import { Button } from '@mui/material';
import { PageContainer, EmptyState } from '@/components';
import { ROUTES } from '@/routes/paths';

export function NotFoundPage(): JSX.Element {
  return (
    <PageContainer>
      <EmptyState
        title="Page not found"
        description="The page you are looking for does not exist or has moved."
        action={
          <Button variant="contained" component={RouterLink} to={ROUTES.dashboard}>
            Back to dashboard
          </Button>
        }
      />
    </PageContainer>
  );
}
