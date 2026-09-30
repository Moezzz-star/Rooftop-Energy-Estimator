import { useState, type MouseEvent } from 'react';
import {
  Avatar,
  Divider,
  IconButton,
  ListItemIcon,
  Menu,
  MenuItem,
  Tooltip,
  Typography,
} from '@mui/material';
import LogoutIcon from '@mui/icons-material/Logout';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks';
import { ROUTES } from '@/routes/paths';

/** AppBar user menu showing the current account and a logout action. */
export function UserMenu(): JSX.Element {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const open = Boolean(anchorEl);

  const handleOpen = (event: MouseEvent<HTMLElement>): void => setAnchorEl(event.currentTarget);
  const handleClose = (): void => setAnchorEl(null);
  const handleLogout = (): void => {
    handleClose();
    logout();
    navigate(ROUTES.login, { replace: true });
  };

  const initial = user?.email.charAt(0).toUpperCase() ?? '?';

  return (
    <>
      <Tooltip title="Account">
        <IconButton
          onClick={handleOpen}
          size="small"
          aria-label="Open account menu"
          aria-haspopup="true"
          aria-expanded={open}
          aria-controls={open ? 'user-menu' : undefined}
        >
          <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.main' }}>{initial}</Avatar>
        </IconButton>
      </Tooltip>
      <Menu id="user-menu" anchorEl={anchorEl} open={open} onClose={handleClose}>
        <Typography variant="body2" sx={{ px: 2, py: 1 }} color="text.secondary">
          {user?.email}
        </Typography>
        <Divider />
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <LogoutIcon fontSize="small" />
          </ListItemIcon>
          Sign out
        </MenuItem>
      </Menu>
    </>
  );
}
