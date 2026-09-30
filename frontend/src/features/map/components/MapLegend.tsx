import { Box, Stack, Typography } from '@mui/material';
import { SOLAR_RAMP, type SolarMetricConfig } from '../mapStyle';

export interface MapLegendProps {
  metric: SolarMetricConfig;
  domain: [number, number];
}

const RANGE_FORMAT = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

/** Colour-ramp legend for the active thematic metric. */
export function MapLegend({ metric, domain }: MapLegendProps): JSX.Element {
  const [min, max] = domain;
  const gradient = `linear-gradient(to right, ${SOLAR_RAMP.join(', ')})`;

  return (
    <Box
      component="figure"
      aria-label={`Legend: ${metric.label} in ${metric.unit}`}
      sx={{ m: 0 }}
    >
      <Typography component="figcaption" variant="caption" color="text.secondary">
        {metric.label} ({metric.unit})
      </Typography>
      <Box
        aria-hidden
        sx={{
          height: 10,
          width: 160,
          borderRadius: 0.5,
          background: gradient,
          border: 1,
          borderColor: 'divider',
          mt: 0.5,
        }}
      />
      <Stack direction="row" justifyContent="space-between" sx={{ width: 160, mt: 0.25 }}>
        <Typography variant="caption" color="text.secondary">
          {RANGE_FORMAT.format(min)}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {RANGE_FORMAT.format(max)}
        </Typography>
      </Stack>
    </Box>
  );
}
