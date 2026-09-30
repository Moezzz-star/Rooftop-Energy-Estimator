import type { TypographyVariantsOptions } from '@mui/material/styles';

/**
 * Design tokens. Restrained palette: primary green (energy/sustainability),
 * secondary blue (trust/analytics), and a solar accent (amber/orange) used
 * sparingly for solar-yield emphasis. `solar` is exposed as a custom palette
 * key (see theme module augmentation).
 */
export const brandColors = {
  green: {
    light: '#4caf72',
    main: '#2e7d4f',
    dark: '#1b5e35',
    contrastText: '#ffffff',
  },
  blue: {
    light: '#4f83cc',
    main: '#1565c0',
    dark: '#0d47a1',
    contrastText: '#ffffff',
  },
  solar: {
    light: '#ffb74d',
    main: '#f59e0b',
    dark: '#c77700',
    contrastText: '#1a1a1a',
  },
} as const;

export const shapeTokens = {
  borderRadius: 10,
} as const;

export const typographyTokens: TypographyVariantsOptions = {
  fontFamily: [
    'Inter',
    'Roboto',
    '-apple-system',
    'BlinkMacSystemFont',
    '"Segoe UI"',
    'Arial',
    'sans-serif',
  ].join(','),
  h1: { fontSize: '2.25rem', fontWeight: 700, lineHeight: 1.2 },
  h2: { fontSize: '1.75rem', fontWeight: 700, lineHeight: 1.25 },
  h3: { fontSize: '1.375rem', fontWeight: 600, lineHeight: 1.3 },
  h4: { fontSize: '1.125rem', fontWeight: 600 },
  button: { textTransform: 'none', fontWeight: 600 },
};
