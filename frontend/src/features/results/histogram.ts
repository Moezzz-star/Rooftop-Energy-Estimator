/** Pure client-side histogram bucketing for distribution charts. */

export interface HistogramBucket {
  /** Human-readable bucket range label, e.g. "0–100". */
  label: string;
  /** Inclusive lower bound of the bucket. */
  from: number;
  /** Exclusive upper bound of the bucket (inclusive for the final bucket). */
  to: number;
  /** Number of values that fell into this bucket. */
  count: number;
}

const LABEL_FORMAT = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

/**
 * Bucket numeric values into `bucketCount` equal-width bins spanning
 * [min, max]. Non-finite values are ignored. Returns an empty array when there
 * are no usable values. A degenerate range (all equal) collapses to a single
 * bucket so the chart still renders meaningfully.
 */
export function bucketize(values: number[], bucketCount = 8): HistogramBucket[] {
  const usable = values.filter((value) => Number.isFinite(value));
  if (usable.length === 0) return [];

  const min = Math.min(...usable);
  const max = Math.max(...usable);

  if (max === min) {
    return [{ label: LABEL_FORMAT.format(min), from: min, to: min, count: usable.length }];
  }

  const bins = Math.max(1, Math.floor(bucketCount));
  const width = (max - min) / bins;
  const buckets: HistogramBucket[] = Array.from({ length: bins }, (_unused, index) => {
    const from = min + width * index;
    const to = index === bins - 1 ? max : min + width * (index + 1);
    return {
      label: `${LABEL_FORMAT.format(Math.round(from))}–${LABEL_FORMAT.format(Math.round(to))}`,
      from,
      to,
      count: 0,
    };
  });

  for (const value of usable) {
    let index = Math.floor((value - min) / width);
    if (index >= bins) index = bins - 1;
    if (index < 0) index = 0;
    buckets[index]!.count += 1;
  }

  return buckets;
}
