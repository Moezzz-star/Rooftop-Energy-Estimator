import { Box, Card, CardContent, Typography } from '@mui/material';
import type { ResultsSummaryDetail } from '../schemas';
import { formatInt, formatArea, formatCapacity, formatEnergy } from '../format';

export interface ZoneSummaryProps {
  summary: ResultsSummaryDetail;
}

interface Metric {
  label: string;
  value: string;
}

/** Average per building, preferring a server-provided average, else derived. */
function perBuilding(total: number, count: number, provided?: number): number {
  if (provided !== undefined) return provided;
  return count > 0 ? total / count : 0;
}

/** Zone-level summary cards: counts, totals and averages for an analysis. */
export function ZoneSummary({ summary }: ZoneSummaryProps): JSX.Element {
  const count = summary.building_count;

  const totals: Metric[] = [
    { label: 'Buildings detected', value: formatInt(count) },
    { label: 'Total roof area', value: formatArea(summary.total_area_m2) },
    { label: 'Total capacity', value: formatCapacity(summary.total_capacity_kwp) },
    { label: 'Estimated annual energy', value: formatEnergy(summary.total_annual_kwh) },
  ];

  const averages: Metric[] = [
    {
      label: 'Avg roof area per building',
      value: formatArea(perBuilding(summary.total_area_m2, count, summary.average_area_m2)),
    },
    {
      label: 'Avg annual energy per building',
      value: formatEnergy(
        perBuilding(summary.total_annual_kwh, count, summary.average_annual_kwh),
      ),
    },
  ];

  if (summary.total_usable_area_m2 !== undefined) {
    averages.push({
      label: 'Total usable roof area',
      value: formatArea(summary.total_usable_area_m2),
    });
  }

  const renderCards = (metrics: Metric[], label: string): JSX.Element => (
    <Box
      component="ul"
      aria-label={label}
      sx={{
        listStyle: 'none',
        p: 0,
        m: 0,
        display: 'grid',
        gap: 2,
        gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
      }}
    >
      {metrics.map((metric) => (
        <Box component="li" key={metric.label}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="caption" color="text.secondary" component="p">
                {metric.label}
              </Typography>
              <Typography variant="h3" component="p" sx={{ mt: 0.5 }}>
                {metric.value}
              </Typography>
            </CardContent>
          </Card>
        </Box>
      ))}
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {renderCards(totals, 'Zone totals')}
      <Typography variant="h4" component="h3">
        Averages
      </Typography>
      {renderCards(averages, 'Zone averages')}
    </Box>
  );
}
