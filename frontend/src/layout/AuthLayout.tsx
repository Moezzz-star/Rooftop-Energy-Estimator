import type { ReactNode } from 'react';
import { Box, Container, Paper, Stack, Typography } from '@mui/material';
import SolarPowerIcon from '@mui/icons-material/SolarPower';
import { DisclaimerBanner } from '@/components';

export interface AuthLayoutProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  /** Secondary content below the card (e.g. a link to the other auth page). */
  footer?: ReactNode;
}

/** Centered card layout for the public login/register pages. */
export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps): JSX.Element {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        bgcolor: 'background.default',
        py: 6,
      }}
    >
      <Container maxWidth="xs" component="main">
        <Stack spacing={1} alignItems="center" sx={{ mb: 3 }}>
          <SolarPowerIcon color="primary" sx={{ fontSize: 40 }} />
          <Typography variant="h3" component="h1" textAlign="center">
            {title}
          </Typography>
          {subtitle && (
            <Typography color="text.secondary" textAlign="center">
              {subtitle}
            </Typography>
          )}
        </Stack>
        <Paper variant="outlined" sx={{ p: { xs: 3, sm: 4 } }}>
          {children}
        </Paper>
        {footer && (
          <Box sx={{ mt: 2, textAlign: 'center' }}>{footer}</Box>
        )}
        <DisclaimerBanner variant="footer" />
      </Container>
    </Box>
  );
}
