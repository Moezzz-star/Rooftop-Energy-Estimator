import type { ReactNode } from 'react';
import { Box, Paper, Typography } from '@mui/material';

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  /** Optional call-to-action (e.g. a create button). */
  action?: ReactNode;
}

/** Meaningful empty-state placeholder for lists/collections. */
export function EmptyState({ title, description, icon, action }: EmptyStateProps): JSX.Element {
  return (
    <Paper
      variant="outlined"
      sx={{ p: 4, textAlign: 'center', borderStyle: 'dashed', bgcolor: 'transparent' }}
    >
      <Box display="flex" flexDirection="column" alignItems="center" gap={1.5}>
        {icon && (
          <Box sx={{ color: 'text.secondary', fontSize: 48, lineHeight: 0 }} aria-hidden>
            {icon}
          </Box>
        )}
        <Typography variant="h4" component="h2">
          {title}
        </Typography>
        {description && (
          <Typography color="text.secondary" sx={{ maxWidth: 420 }}>
            {description}
          </Typography>
        )}
        {action && <Box sx={{ mt: 1 }}>{action}</Box>}
      </Box>
    </Paper>
  );
}
