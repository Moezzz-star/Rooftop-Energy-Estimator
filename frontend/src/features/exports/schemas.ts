import { z } from 'zod';

/** Backend export kinds (code-architecture §4 #20-#21, ExportArtifact.kind). */
export const exportKindSchema = z.enum(['geojson', 'csv', 'pdf']);
export type ExportKind = z.infer<typeof exportKindSchema>;

/**
 * ExportArtifact status is a free-form backend string; we classify it into
 * ready / failed / pending rather than hard-coding an enum we cannot guarantee.
 */
export const exportArtifactSchema = z.object({
  id: z.string().uuid(),
  kind: exportKindSchema,
  status: z.string(),
  checksum: z.string().nullable().default(null),
  bytes: z.number().int().nonnegative().nullable().default(null),
  created_at: z.string(),
  /** Authenticated/signed download URL; null until the artifact is built. */
  download_url: z.string().nullable().default(null),
});
export type ExportArtifact = z.infer<typeof exportArtifactSchema>;

/** Tolerate either a DRF paginated envelope or a bare array for the list. */
export const exportListSchema = z.union([
  z.object({
    count: z.number().int().nonnegative(),
    next: z.string().url().nullable(),
    previous: z.string().url().nullable(),
    results: z.array(exportArtifactSchema),
  }),
  z.array(exportArtifactSchema),
]);
export type ExportListResponse = z.infer<typeof exportListSchema>;

const READY_STATUSES = new Set(['ready', 'completed', 'succeeded', 'success', 'done']);
const FAILED_STATUSES = new Set(['failed', 'error', 'errored', 'cancelled', 'canceled']);

/** An artifact is downloadable once its status is terminal-ready and a URL exists. */
export function isExportReady(artifact: ExportArtifact): boolean {
  return READY_STATUSES.has(artifact.status.toLowerCase()) && artifact.download_url !== null;
}

export function isExportFailed(artifact: ExportArtifact): boolean {
  return FAILED_STATUSES.has(artifact.status.toLowerCase());
}

/** Polling terminal state: either ready-with-url or failed. */
export function isExportTerminal(artifact: ExportArtifact): boolean {
  return isExportReady(artifact) || isExportFailed(artifact);
}

/** File extension for a kind (used for the download filename). */
export function exportFileExtension(kind: ExportKind): string {
  return kind === 'geojson' ? 'geojson' : kind;
}
