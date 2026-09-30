import { z } from 'zod';

/** Backend consistent error envelope (code-architecture.md §6). */
export const errorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.unknown().optional(),
  }),
});

export type ErrorEnvelope = z.infer<typeof errorEnvelopeSchema>;

/**
 * Normalized error thrown by the HTTP client for any non-2xx response or
 * network/parse failure. UI (ErrorState, form handlers) reads `.message` and
 * `.code`; forms may inspect `.details` for field errors.
 */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: unknown;

  constructor(params: { code: string; message: string; status: number; details?: unknown }) {
    super(params.message);
    this.name = 'ApiError';
    this.code = params.code;
    this.status = params.status;
    this.details = params.details;
  }

  /** True when the error carries a per-field `details` map usable by forms. */
  get fieldErrors(): Record<string, string> | null {
    if (this.details && typeof this.details === 'object' && !Array.isArray(this.details)) {
      const out: Record<string, string> = {};
      for (const [key, value] of Object.entries(this.details as Record<string, unknown>)) {
        if (typeof value === 'string') out[key] = value;
        else if (Array.isArray(value) && typeof value[0] === 'string') out[key] = value[0];
      }
      return Object.keys(out).length > 0 ? out : null;
    }
    return null;
  }
}

/** Parse an arbitrary error body into an ApiError, tolerating non-envelope bodies. */
export function toApiError(body: unknown, status: number): ApiError {
  const parsed = errorEnvelopeSchema.safeParse(body);
  if (parsed.success) {
    return new ApiError({
      code: parsed.data.error.code,
      message: parsed.data.error.message,
      status,
      details: parsed.data.error.details,
    });
  }
  return new ApiError({
    code: 'unknown_error',
    message:
      status === 0
        ? 'Network error — please check your connection and try again.'
        : `Request failed with status ${status}.`,
    status,
  });
}
