import {
  Box,
  Chip,
  List,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import { DisclaimerBanner } from '@/components';
import type { DataQuality, ResultsSummaryDetail } from '../schemas';

export interface TransparencyPanelProps {
  summary: ResultsSummaryDetail;
}

const METHODOLOGY: readonly string[] = [
  'Building footprints are detected by a U-Net segmentation model from the supplied imagery.',
  'Usable roof area assumes 70% of each footprint; module power density is 200 W/m².',
  'Energy is simulated hourly for a full year using pvlib clear-sky (Ineichen) irradiance.',
  'A fixed default tilt and azimuth are applied; assumed system losses are 14%.',
  'These are the frozen assumptions for this analysis and reproduce identical numbers on re-open.',
];

const IMPACT_COLOR: Record<
  NonNullable<DataQuality['factors'][number]['impact']>,
  'success' | 'default' | 'warning'
> = {
  positive: 'success',
  neutral: 'default',
  negative: 'warning',
};

function DataQualityBlock({ dataQuality }: { dataQuality: DataQuality }): JSX.Element {
  return (
    <Box>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }} flexWrap="wrap" useFlexGap>
        <Typography variant="subtitle2" component="p">
          Data quality indicator
        </Typography>
        <Chip size="small" label={dataQuality.indicator} />
        <Typography variant="caption" color="text.secondary">
          (transparency signal — not a calibrated confidence)
        </Typography>
      </Stack>

      {dataQuality.factors.length > 0 && (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
          {dataQuality.factors.map((factor) => (
            <Chip
              key={factor.label}
              size="small"
              variant="outlined"
              color={factor.impact ? IMPACT_COLOR[factor.impact] : 'default'}
              label={factor.detail ? `${factor.label}: ${factor.detail}` : factor.label}
            />
          ))}
        </Stack>
      )}

      {dataQuality.notes.length > 0 && (
        <List dense disablePadding aria-label="Data quality notes">
          {dataQuality.notes.map((note) => (
            <ListItem key={note} disableGutters sx={{ py: 0.25 }}>
              <ListItemText primaryTypographyProps={{ variant: 'body2' }} primary={note} />
            </ListItem>
          ))}
        </List>
      )}
    </Box>
  );
}

/**
 * Methodology, assumptions, attribution, optional §16 data-quality signal and
 * the mandatory DEC-02 disclaimer. Data quality is explicitly framed as a
 * transparency indicator, never a calibrated confidence.
 */
export function TransparencyPanel({ summary }: TransparencyPanelProps): JSX.Element {
  return (
    <Paper variant="outlined" sx={{ p: 2.5 }}>
      <Stack spacing={2}>
        <Box>
          <Typography variant="h4" component="h3" gutterBottom>
            Methodology and assumptions
          </Typography>
          <List dense disablePadding aria-label="Methodology and assumptions">
            {METHODOLOGY.map((item) => (
              <ListItem key={item} disableGutters sx={{ py: 0.25 }}>
                <ListItemText primaryTypographyProps={{ variant: 'body2' }} primary={item} />
              </ListItem>
            ))}
          </List>
        </Box>

        {summary.data_quality ? (
          <DataQualityBlock dataQuality={summary.data_quality} />
        ) : (
          <Typography variant="body2" color="text.secondary">
            No aggregate data-quality signal was provided for this analysis; per-building
            warnings, where present, are shown in each building&apos;s detail.
          </Typography>
        )}

        <Typography variant="caption" color="text.secondary">
          Building labels derived from © OpenStreetMap contributors, ODbL. Solar model: pvlib
          (BSD-3).
        </Typography>

        <DisclaimerBanner variant="banner" />
      </Stack>
    </Paper>
  );
}
