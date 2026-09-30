import { z } from 'zod';

export const jobStatusSchema = z.enum([
  'queued',
  'running',
  'completed',
  'failed',
  'cancelled',
]);

export const jobStageStatusSchema = z.enum([
  'pending',
  'running',
  'succeeded',
  'failed',
  'skipped',
]);

export type JobStatus = z.infer<typeof jobStatusSchema>;
export type JobStageStatus = z.infer<typeof jobStageStatusSchema>;

export const jobStageSchema = z.object({
  name: z.string(),
  sequence: z.number().int().nonnegative(),
  status: jobStageStatusSchema,
  duration_ms: z.number().nonnegative().nullable().default(null),
  detail: z.record(z.string(), z.unknown()).nullable().default(null),
});

export const jobSchema = z.object({
  id: z.string().uuid(),
  analysis: z.string().uuid(),
  status: jobStatusSchema,
  stages: z.array(jobStageSchema),
  queued_at: z.string().datetime({ offset: true }).nullable().default(null),
  started_at: z.string().datetime({ offset: true }).nullable().default(null),
  finished_at: z.string().datetime({ offset: true }).nullable().default(null),
  error: z.record(z.string(), z.unknown()).nullable().default(null),
});

export type JobStage = z.infer<typeof jobStageSchema>;
export type Job = z.infer<typeof jobSchema>;

/** Job statuses that stop polling. */
export const TERMINAL_JOB_STATUSES: readonly JobStatus[] = [
  'completed',
  'failed',
  'cancelled',
];

export function isTerminalJobStatus(status: JobStatus): boolean {
  return TERMINAL_JOB_STATUSES.includes(status);
}
