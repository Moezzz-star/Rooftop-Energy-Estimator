import { useQueryClient } from '@tanstack/react-query';
import { useApiQuery, useApiMutation } from '@/api';
import { usePolling } from '@/hooks';
import { exportsApi } from './api';
import { exportQueryKeys } from './queryKeys';
import { isExportTerminal, type ExportArtifact, type ExportKind } from './schemas';

/** Query: list an analysis's export artifacts. */
export function useExportsList(analysisId: string | undefined, enabled = true) {
  return useApiQuery<ExportArtifact[]>({
    queryKey: exportQueryKeys.listForAnalysis(analysisId ?? 'none'),
    queryFn: (signal) => exportsApi.list(analysisId as string, signal),
    enabled: Boolean(analysisId) && enabled,
  });
}

/** Mutation: request a new export of the given kind for an analysis. */
export function useCreateExport(analysisId: string | undefined) {
  const queryClient = useQueryClient();
  return useApiMutation<ExportArtifact, ExportKind>({
    mutationFn: (kind) => exportsApi.create(analysisId as string, kind),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: exportQueryKeys.listForAnalysis(analysisId ?? 'none'),
      }),
  });
}

/** Poll an export's status until it is ready (with a download URL) or failed. */
export function useExport(exportId: string | null) {
  return usePolling<ExportArtifact>({
    queryKey: exportQueryKeys.detail(exportId ?? 'none'),
    queryFn: (signal) => exportsApi.get(exportId as string, signal),
    isTerminal: isExportTerminal,
    intervalMs: 1500,
    enabled: Boolean(exportId),
  });
}

/** Mutation: download a ready artifact through the authenticated HTTP layer. */
export function useDownloadExport() {
  return useApiMutation<void, ExportArtifact>({
    mutationFn: (artifact) => exportsApi.download(artifact),
  });
}
