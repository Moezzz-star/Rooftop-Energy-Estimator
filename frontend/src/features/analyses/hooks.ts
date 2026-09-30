import { useQueryClient } from '@tanstack/react-query';
import { useApiQuery, useApiMutation, queryKeys } from '@/api';
import type { AnalysisList, Analysis } from '@/schemas';
import { usePolling } from '@/hooks';
import { analysesApi, type CreateAnalysisInput, type ListAnalysesParams } from './api';
import { isTerminalJobStatus, type Job, type SubmitResponse, type AnalysisDetail } from './schemas';

/** Query: analyses belonging to a project. */
export function useProjectAnalyses(projectId: string | undefined, params: ListAnalysesParams = {}) {
  return useApiQuery<AnalysisList>({
    queryKey: queryKeys.analyses.listForProject(projectId ?? 'none'),
    queryFn: (signal) => analysesApi.listForProject(projectId as string, params, signal),
    enabled: Boolean(projectId),
  });
}

/** Query: analysis detail (includes areas for map bbox). */
export function useAnalysis(analysisId: string | undefined) {
  return useApiQuery<AnalysisDetail>({
    queryKey: queryKeys.analyses.detail(analysisId ?? 'none'),
    queryFn: (signal) => analysesApi.get(analysisId as string, signal),
    enabled: Boolean(analysisId),
  });
}

/** Mutation: create a draft analysis under a project. */
export function useCreateAnalysis() {
  const queryClient = useQueryClient();
  return useApiMutation<Analysis, CreateAnalysisInput>({
    mutationFn: (input) => analysesApi.create(input),
    onSuccess: (_analysis, input) =>
      queryClient.invalidateQueries({
        queryKey: queryKeys.analyses.listForProject(input.projectId),
      }),
  });
}

/** Mutation: submit an analysis for processing (generates the Idempotency-Key). */
export function useSubmitAnalysis() {
  return useApiMutation<SubmitResponse, string>({
    mutationFn: (analysisId) => analysesApi.submit(analysisId),
  });
}

/** Poll the processing job until it reaches a terminal status. */
export function useJobPolling(analysisId: string | undefined, intervalMs = 1500) {
  return usePolling<Job>({
    queryKey: queryKeys.analyses.job(analysisId ?? 'none'),
    queryFn: (signal) => analysesApi.getJob(analysisId as string, signal),
    isTerminal: (job) => isTerminalJobStatus(job.status),
    intervalMs,
    enabled: Boolean(analysisId),
  });
}

/** Mutation: request cooperative cancellation of a running job. */
export function useCancelJob(analysisId: string | undefined) {
  const queryClient = useQueryClient();
  return useApiMutation<Job, void>({
    mutationFn: () => analysesApi.cancelJob(analysisId as string),
    onSuccess: (job) => {
      queryClient.setQueryData(queryKeys.analyses.job(analysisId ?? 'none'), job);
    },
  });
}
