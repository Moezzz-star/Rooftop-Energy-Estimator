/** Feature-local TanStack Query keys for exports. */
export const exportQueryKeys = {
  all: ['exports'] as const,
  listForAnalysis: (analysisId: string) => ['exports', 'analysis', analysisId] as const,
  detail: (exportId: string) => ['exports', 'detail', exportId] as const,
};
