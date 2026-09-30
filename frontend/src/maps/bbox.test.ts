import { describe, it, expect } from 'vitest';
import { serializeBBox, parseBBox, zoomToSimplifyMeters, type BBox } from './bbox';

describe('bbox helpers', () => {
  const bbox: BBox = [-1.5, 50.1, -1.2, 50.4];

  it('round-trips a bbox through serialize/parse', () => {
    const parsed = parseBBox(serializeBBox(bbox));
    expect(parsed).toEqual(bbox);
  });

  it('returns null for malformed bbox strings', () => {
    expect(parseBBox('1,2,3')).toBeNull();
    expect(parseBBox('a,b,c,d')).toBeNull();
  });

  it('maps higher zoom to finer simplification tolerance', () => {
    expect(zoomToSimplifyMeters(19)).toBeLessThan(zoomToSimplifyMeters(9));
    expect(zoomToSimplifyMeters(18)).toBe(0.25);
  });
});
