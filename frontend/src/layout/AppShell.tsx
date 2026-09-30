import { AppBar, Box, Button, Container, Stack, Toolbar, Typography } from '@mui/material';
import SolarPowerIcon from '@mui/icons-material/SolarPower';
import { Link as RouterLink, Outlet } from 'react-router-dom';
import { ThemeModeToggle } from '@/theme';
import { DisclaimerBanner } from '@/components';
import { ROUTES } from '@/routes/paths';
import { UserMenu } from './UserMenu';

/**
 * Authenticated app shell: responsive AppBar (brand, theme toggle, account
 * menu), the routed page via <Outlet />, and the global disclaimer footer.
 */
export function AppShell(): JSX.Element {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="sticky" color="default" elevation={1} enableColorOnDark>
        <Toolbar>
          <Stack
            component={RouterLink}
            to={ROUTES.dashboard}
            direction="row"
            spacing={1}
            alignItems="center"
            sx={{ textDecoration: 'none', color: 'inherit', flexGrow: 1 }}
          >
            <SolarPowerIcon color="primary" />
            <Typography variant="h4" component="span" sx={{ fontWeight: 700 }}>
              Rooftop Energy Estimator
            </Typography>
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            <Button component={RouterLink} to={ROUTES.dashboard} color="inherit">
              Dashboard
            </Button>
            <ThemeModeToggle />
            <UserMenu />
          </Stack>
        </Toolbar>
      </AppBar>

      <Box component="div" sx={{ flexGrow: 1 }}>
        <Outlet />
      </Box>

      <Container maxWidth="lg">
        <DisclaimerBanner variant="footer" />
      </Container>
    </Box>
  );
}
