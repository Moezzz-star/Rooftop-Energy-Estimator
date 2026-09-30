import { describe, it, expect } from 'vitest';
import { bucketize } from './histogram';

describe('bucketize', () => {
  it('returns no buckets for an empty or all-non-finite input', () => {
    expect(bucketize([])).toEqual([]);
    expect(bucketize([Number.NaN, Number.POSITIVE_INFINITY])).toEqual([]);
  });

  it('collapses a single distinct value into one bucket', () => {
    const buckets = bucketize([5, 5, 5]);
    expect(buckets).toHaveLength(1);
    expect(buckets[0]?.count).toBe(3);
  });

  it('distributes values across equal-width buckets, including the max', () => {
    const buckets = bucketize([0, 10, 20, 30, 40, 50, 60, 70, 80], 8);
    expect(buckets).toHaveLength(8);
    const total = buckets.reduce((sum, bucket) => sum + bucket.count, 0);
    expect(total).toBe(9);
    // The maximum value lands in the final bucket, never overflowing.
    expect(buckets[buckets.length - 1]?.count).toBeGreaterThanOrEqual(1);
  });
});
