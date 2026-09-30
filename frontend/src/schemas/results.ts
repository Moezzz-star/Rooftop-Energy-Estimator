import { z } from 'zod';

/** Summary from GET /analyses/{id}/results/. */
export const resultsSummarySchema = z.object({
  building_count: z.number().int().nonnegative(),
  total_area_m2: z.number().nonnegative(),
  total_capacity_kwp: z.number().nonnegative(),
  total_annual_kwh: z.number().nonnegative(),
  disclaimer: z.string(),
});

export type ResultsSummary = z.infer<typeof resultsSummarySchema>;
