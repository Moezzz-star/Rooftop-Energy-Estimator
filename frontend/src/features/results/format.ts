/** Locale-aware number formatting helpers for results/solar values. */

const NUMBER = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
const NUMBER_1DP = new Intl.NumberFormat(undefined, {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function formatInt(value: number): string {
  return NUMBER.format(Math.round(value));
}

export function formatArea(m2: number): string {
  return `${NUMBER.format(Math.round(m2))} m²`;
}

export function formatCapacity(kwp: number): string {
  return `${NUMBER_1DP.format(kwp)} kWp`;
}

export function formatEnergy(kwh: number): string {
  return `${NUMBER.format(Math.round(kwh))} kWh`;
}

export function formatDegrees(deg: number): string {
  return `${NUMBER.format(Math.round(deg))}°`;
}

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export const MONTH_LABELS = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
] as const;
