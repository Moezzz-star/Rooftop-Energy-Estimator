import { Alert, AlertTitle, Typography } from '@mui/material';
import { PageContainer } from './PageContainer';

export interface PlaceholderPageProps {
  title: string;
  /** What the future implementation should do here. */
  todo: string;
}

/**
 * Standard "not built yet" page body. Placeholder page files under `pages/`
 * render this until the responsible engineer replaces the page body with the
 * real screen. Not intended for production routes long-term.
 */
export function PlaceholderPage({ title, todo }: PlaceholderPageProps): JSX.Element {
  return (
    <PageContainer title={title}>
      <Alert severity="info" variant="outlined">
        <AlertTitle>Coming soon</AlertTitle>
        <Typography variant="body2">{todo}</Typography>
      </Alert>
    </PageContainer>
  );
}
