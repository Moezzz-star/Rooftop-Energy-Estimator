import { z } from 'zod';
import { polygonSchema, multiPolygonSchema } from '@/schemas';

/**
 * Feature-local schemas that match the live backend responses for the analysis
 * job + submit endpoints. These intentionally differ from the shared
 * `@/schemas` job DTO: the backend emits `analysis_id` (not `analysis`) and uses
 * the `succeeded` terminal status (not `completed`).
 */

export const jobStatusSchema = z.enum(['queued', 'running', 'succeeded', 'failed', 'cancelled']);
export type JobStatus = z.infer<typeof jobStatusSchema>;

export const jobStageStatusSchema = z.enum([
  'pending',
  'running',
  'succeeded',
  'failed',
  'skipped',
]);
export type JobStageStatus = z.infer<typeof jobStageStatusSchema>;

export const jobStageSchema = z.object({
  name: z.string(),
  sequence: z.number().int().nonnegative(),
  status: jobStageStatusSchema,
  started_at: z.string().datetime({ offset: true }).nullable().default(null),
  finished_at: z.string().datetime({ offset: true }).nullable().default(null),
  duration_ms: z.number().nonnegative().nullable().default(null),
  detail: z.record(z.string(), z.unknown()).nullable().default(null),
});
export type JobStage = z.infer<typeof jobStageSchema>;

export const jobSchema = z.object({
  id: z.string().uuid(),
  analysis_id: z.string().uuid(),
  status: jobStatusSchema,
  stages: z.array(jobStageSchema),
  cancel_requested: z.boolean().default(false),
  queued_at: z.string().datetime({ offset: true }).nullable().default(null),
  started_at: z.string().datetime({ offset: true }).nullable().default(null),
  finished_at: z.string().datetime({ offset: true }).nullable().default(null),
  error: z.record(z.string(), z.unknown()).nullable().default(null),
});
export type Job = z.infer<typeof jobSchema>;

const TERMINAL_JOB_STATUSES: ReadonlySet<JobStatus> = new Set<JobStatus>([
  'succeeded',
  'failed',
  'cancelled',
]);

/** True once the job reaches a terminal state (polling should stop). */
export function isTerminalJobStatus(status: JobStatus): boolean {
  return TERMINAL_JOB_STATUSES.has(status);
}

/** Human-readable message from a job's error envelope, if any. */
export function jobErrorMessage(error: Job['error']): string | null {
  if (!error) return null;
  const message = error.message;
  return typeof message === 'string' && message.length > 0 ? message : null;
}

/** Body returned by POST /analyses/{id}/submit/ (202). */
export const submitResponseSchema = z.object({
  analysis: z.object({ id: z.string().uuid(), status: z.string() }),
  job: z.object({ id: z.string(), status: z.string().nullable() }).nullable(),
});
export type SubmitResponse = z.infer<typeof submitResponseSchema>;

/** One area row from the analysis detail `areas` array. */
export const analysisAreaRowSchema = z.object({
  id: z.union([z.string(), z.number()]),
  label: z.string().nullable().default(null),
  area: z.union([polygonSchema, multiPolygonSchema]),
});

/**
 * Analysis detail as returned by GET /analyses/{id}/ — includes the `areas`
 * array (used to derive the map bbox on the results screen).
 */
export const analysisDetailSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  status: z.string(),
  project: z.string().uuid(),
  areas: z.array(analysisAreaRowSchema).default([]),
  created_at: z.string().datetime({ offset: true }),
  submitted_at: z.string().datetime({ offset: true }).nullable().default(null),
  completed_at: z.string().datetime({ offset: true }).nullable().default(null),
});
export type AnalysisDetail = z.infer<typeof analysisDetailSchema>;
