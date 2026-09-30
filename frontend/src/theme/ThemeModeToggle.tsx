import { useState, type MouseEvent } from 'react';
import { IconButton, Menu, MenuItem, ListItemIcon, ListItemText, Tooltip } from '@mui/material';
import LightModeIcon from '@mui/icons-material/LightMode';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import SettingsBrightnessIcon from '@mui/icons-material/SettingsBrightness';
import { useThemeMode, type ThemeMode } from './ThemeModeContext';

const OPTIONS: { value: ThemeMode; label: string; icon: JSX.Element }[] = [
  { value: 'light', label: 'Light', icon: <LightModeIcon fontSize="small" /> },
  { value: 'dark', label: 'Dark', icon: <DarkModeIcon fontSize="small" /> },
  { value: 'system', label: 'System', icon: <SettingsBrightnessIcon fontSize="small" /> },
];

/** AppBar control to switch between light, dark and system color modes. */
export function ThemeModeToggle(): JSX.Element {
  const { mode, resolvedMode, setMode } = useThemeMode();
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const open = Boolean(anchorEl);

  const handleOpen = (event: MouseEvent<HTMLElement>): void => setAnchorEl(event.currentTarget);
  const handleClose = (): void => setAnchorEl(null);
  const handleSelect = (value: ThemeMode): void => {
    setMode(value);
    handleClose();
  };

  return (
    <>
      <Tooltip title="Change theme">
        <IconButton
          onClick={handleOpen}
          color="inherit"
          aria-label="Change theme"
          aria-haspopup="true"
          aria-expanded={open}
          aria-controls={open ? 'theme-mode-menu' : undefined}
        >
          {resolvedMode === 'dark' ? <DarkModeIcon /> : <LightModeIcon />}
        </IconButton>
      </Tooltip>
      <Menu id="theme-mode-menu" anchorEl={anchorEl} open={open} onClose={handleClose}>
        {OPTIONS.map((option) => (
          <MenuItem
            key={option.value}
            selected={option.value === mode}
            onClick={() => handleSelect(option.value)}
          >
            <ListItemIcon>{option.icon}</ListItemIcon>
            <ListItemText>{option.label}</ListItemText>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
