import { Box, CircularProgress, Typography } from '@mui/material';

export interface LoadingStateProps {
  label?: string;
  /** Minimum vertical space so layout doesn't jump. */
  minHeight?: number | string;
}

/** Accessible loading indicator for async views. */
export function LoadingState({
  label = 'Loading…',
  minHeight = 200,
}: LoadingStateProps): JSX.Element {
  return (
    <Box
      role="status"
      aria-live="polite"
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      gap={2}
      sx={{ minHeight }}
    >
      <CircularProgress aria-hidden />
      <Typography color="text.secondary">{label}</Typography>
    </Box>
  );
}
