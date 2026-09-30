import { Alert, AlertTitle, Box, Button } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  /** When provided, renders a retry button. */
  onRetry?: () => void;
  retryLabel?: string;
}

/** Standard error surface with an optional retry affordance. */
export function ErrorState({
  title = 'Something went wrong',
  message = 'The request could not be completed. Please try again.',
  onRetry,
  retryLabel = 'Retry',
}: ErrorStateProps): JSX.Element {
  return (
    <Box sx={{ my: 2 }}>
      <Alert
        severity="error"
        role="alert"
        action={
          onRetry ? (
            <Button color="inherit" size="small" startIcon={<RefreshIcon />} onClick={onRetry}>
              {retryLabel}
            </Button>
          ) : undefined
        }
      >
        <AlertTitle>{title}</AlertTitle>
        {message}
      </Alert>
    </Box>
  );
}
