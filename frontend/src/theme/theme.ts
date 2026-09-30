import { createTheme, type Theme } from '@mui/material/styles';
import { brandColors, shapeTokens, typographyTokens } from './tokens';

/** Resolved (concrete) color scheme actually applied to the DOM. */
export type ResolvedMode = 'light' | 'dark';

/**
 * Augment MUI's palette with a `solar` accent so components can use
 * `theme.palette.solar.main` with full type-safety instead of hardcoded hex.
 */
declare module '@mui/material/styles' {
  interface Palette {
    solar: Palette['primary'];
  }
  interface PaletteOptions {
    solar?: PaletteOptions['primary'];
  }
}

export function createAppTheme(mode: ResolvedMode): Theme {
  return createTheme({
    palette: {
      mode,
      primary: brandColors.green,
      secondary: brandColors.blue,
      solar: brandColors.solar,
      ...(mode === 'light'
        ? {
            background: { default: '#f6f8f6', paper: '#ffffff' },
          }
        : {
            background: { default: '#0f1512', paper: '#161d19' },
          }),
    },
    shape: shapeTokens,
    typography: typographyTokens,
    components: {
      MuiButton: {
        defaultProps: { disableElevation: true },
      },
    },
  });
}
