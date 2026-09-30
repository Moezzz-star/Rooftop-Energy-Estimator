import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { ThemeProvider as MuiThemeProvider, CssBaseline } from '@mui/material';
import { createAppTheme } from './theme';
import {
  ThemeModeContext,
  THEME_MODE_STORAGE_KEY,
  readStoredMode,
  resolveMode,
  systemPrefersDark,
  type ThemeMode,
} from './ThemeModeContext';

/**
 * Provides MUI theming plus the light/dark/system mode context. The selected
 * mode is persisted in localStorage; "system" tracks prefers-color-scheme live.
 */
export function AppThemeProvider({ children }: { children: ReactNode }): JSX.Element {
  const [mode, setModeState] = useState<ThemeMode>(() => readStoredMode());
  const [systemDark, setSystemDark] = useState<boolean>(() => systemPrefersDark());

  useEffect(() => {
    if (!window.matchMedia) return;
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const listener = (event: MediaQueryListEvent): void => setSystemDark(event.matches);
    mql.addEventListener('change', listener);
    return () => mql.removeEventListener('change', listener);
  }, []);

  const setMode = useCallback((next: ThemeMode): void => {
    setModeState(next);
    window.localStorage.setItem(THEME_MODE_STORAGE_KEY, next);
  }, []);

  const resolvedMode = useMemo(
    () => (mode === 'system' ? (systemDark ? 'dark' : 'light') : resolveMode(mode)),
    [mode, systemDark],
  );

  const theme = useMemo(() => createAppTheme(resolvedMode), [resolvedMode]);

  const contextValue = useMemo(
    () => ({ mode, resolvedMode, setMode }),
    [mode, resolvedMode, setMode],
  );

  return (
    <ThemeModeContext.Provider value={contextValue}>
      <MuiThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </MuiThemeProvider>
    </ThemeModeContext.Provider>
  );
}
