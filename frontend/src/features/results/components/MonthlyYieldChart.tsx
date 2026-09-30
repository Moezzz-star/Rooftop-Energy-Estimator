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
import { MONTH_LABELS, formatEnergy } from '../format';

export interface MonthlyYieldChartProps {
  /** Twelve monthly kWh values (Jan..Dec). Extra/short arrays are tolerated. */
  monthlyKwh: number[];
}

interface ChartDatum {
  month: string;
  kwh: number;
}

/**
 * Monthly energy bar chart with an always-present visually-hidden data table so
 * the values are available to screen readers (and deterministic in tests where
 * the SVG chart has no measured size).
 */
export function MonthlyYieldChart({ monthlyKwh }: MonthlyYieldChartProps): JSX.Element {
  const data: ChartDatum[] = monthlyKwh.map((kwh, index) => ({
    month: MONTH_LABELS[index] ?? `M${index + 1}`,
    kwh,
  }));

  return (
    <Box>
      <Typography variant="h4" component="h4" gutterBottom>
        Monthly energy estimate
      </Typography>
      <Box
        sx={{ width: '100%', height: 220 }}
        role="img"
        aria-label="Bar chart of estimated monthly energy in kilowatt-hours"
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="month" fontSize={12} />
            <YAxis fontSize={12} width={48} />
            <Tooltip formatter={(value: number) => formatEnergy(value)} />
            <Bar dataKey="kwh" fill="#1f6feb" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Box>
      <Box component="table" sx={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)' }}>
        <caption>Estimated monthly energy in kilowatt-hours</caption>
        <tbody>
          {data.map((datum) => (
            <tr key={datum.month}>
              <th scope="row">{datum.month}</th>
              <td>{formatEnergy(datum.kwh)}</td>
            </tr>
          ))}
        </tbody>
      </Box>
    </Box>
  );
}
