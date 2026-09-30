import { Box, Typography } from '@mui/material';
import { DEC02_DISCLAIMER } from './disclaimerText';

export interface DisclaimerBannerProps {
  /** `footer` for a subtle page footer, `banner` for an inline callout. */
  variant?: 'footer' | 'banner';
}

/**
 * Displays the canonical DEC-02 estimate disclaimer verbatim. Reused across
 * results, exports and the app footer — do not paraphrase the text.
 */
export function DisclaimerBanner({ variant = 'footer' }: DisclaimerBannerProps): JSX.Element {
  return (
    <Box
      component="aside"
      aria-label="Estimate disclaimer"
      sx={{
        borderTop: variant === 'footer' ? 1 : 0,
        borderColor: 'divider',
        bgcolor: variant === 'banner' ? 'action.hover' : 'transparent',
        borderRadius: variant === 'banner' ? 1 : 0,
        px: variant === 'banner' ? 2 : 0,
        py: variant === 'banner' ? 1.5 : 2,
        mt: variant === 'footer' ? 4 : 0,
      }}
    >
      <Typography variant="caption" color="text.secondary">
        {DEC02_DISCLAIMER}
      </Typography>
    </Box>
  );
}
