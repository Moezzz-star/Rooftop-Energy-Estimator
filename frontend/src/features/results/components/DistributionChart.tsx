import { Box, Typography } from '@mui/material';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { EmptyState } from '@/components';
import { bucketize } from '../histogram';

export interface DistributionChartProps {
  title: string;
  /** Values to bucket into the histogram (e.g. per-building annual kWh). */
  values: number[];
  /** Unit shown on the x-axis label (e.g. "kWh"). */
  unit: string;
  /** Message shown when no values are available for the metric. */
  emptyDescription: string;
  /** Bar/axis colour. */
  color?: string;
}

/**
 * Histogram of a per-building metric, bucketed client-side. Renders a
 * visually-hidden data table alongside the chart so the distribution is
 * available to screen readers and deterministic under jsdom.
 */
export function DistributionChart({
  title,
  values,
  unit,
  emptyDescription,
  color = '#1f6feb',
}: DistributionChartProps): JSX.Element {
  const buckets = bucketize(values);

  return (
    <Box>
      <Typography variant="h4" component="h3" gutterBottom>
        {title}
      </Typography>
      {buckets.length === 0 ? (
        <EmptyState title="Not available" description={emptyDescription} />
      ) : (
        <>
          <Box
            sx={{ width: '100%', height: 220 }}
            role="img"
            aria-label={`Histogram of ${title.toLowerCase()} across buildings, in ${unit}`}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={buckets} margin={{ top: 8, right: 8, bottom: 24, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="label"
                  fontSize={11}
                  interval={0}
                  angle={-30}
                  textAnchor="end"
                  height={48}
                  label={{ value: unit, position: 'insideBottomRight', offset: -4, fontSize: 11 }}
                />
                <YAxis
                  allowDecimals={false}
                  fontSize={12}
                  width={40}
                  label={{ value: 'Buildings', angle: -90, position: 'insideLeft', fontSize: 11 }}
                />
                <Tooltip
                  formatter={(value: number) => [`${value}`, 'Buildings']}
                  labelFormatter={(label: string) => `${label} ${unit}`}
                />
                <Bar dataKey="count" fill={color} radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Box>
          <Box
            component="table"
            sx={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)' }}
          >
            <caption>{`${title} distribution (${unit})`}</caption>
            <thead>
              <tr>
                <th scope="col">Range ({unit})</th>
                <th scope="col">Buildings</th>
              </tr>
            </thead>
            <tbody>
              {buckets.map((bucket) => (
                <tr key={bucket.label}>
                  <th scope="row">{bucket.label}</th>
                  <td>{bucket.count}</td>
                </tr>
              ))}
            </tbody>
          </Box>
        </>
      )}
    </Box>
  );
}
