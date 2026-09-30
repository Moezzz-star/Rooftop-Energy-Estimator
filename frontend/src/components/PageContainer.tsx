import type { ReactNode } from 'react';
import { Container, Box, Typography, Stack } from '@mui/material';

export interface PageContainerProps {
  title?: string;
  description?: string;
  /** Right-aligned actions (e.g. primary buttons) in the page header. */
  actions?: ReactNode;
  children: ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | false;
}

/** Consistent page-level wrapper with an optional titled header row. */
export function PageContainer({
  title,
  description,
  actions,
  children,
  maxWidth = 'lg',
}: PageContainerProps): JSX.Element {
  return (
    <Container maxWidth={maxWidth} component="main" sx={{ py: { xs: 3, md: 4 } }}>
      {(title || actions) && (
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          justifyContent="space-between"
          alignItems={{ xs: 'flex-start', sm: 'center' }}
          spacing={2}
          sx={{ mb: 3 }}
        >
          <Box>
            {title && (
              <Typography variant="h2" component="h1">
                {title}
              </Typography>
            )}
            {description && (
              <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
                {description}
              </Typography>
            )}
          </Box>
          {actions && <Box>{actions}</Box>}
        </Stack>
      )}
      {children}
    </Container>
  );
}
