import { http, parseResponse, type QueryParams } from '@/api';
import {
  analysisSchema,
  analysisListSchema,
  type Analysis,
  type AnalysisList,
  type AnalysisArea,
} from '@/schemas';
import {
  jobSchema,
  submitResponseSchema,
  analysisDetailSchema,
  type Job,
  type SubmitResponse,
  type AnalysisDetail,
} from './schemas';

/** Generate a random idempotency key (RFC 4122 v4 where available). */
function generateIdempotencyKey(): string {
  const cryptoObj = globalThis.crypto as Crypto | undefined;
  if (cryptoObj?.randomUUID) return cryptoObj.randomUUID();
  // Fallback for environments without crypto.randomUUID.
  return `idem-${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
}

export type ListAnalysesParams = {
  ordering?: string;
  page?: number;
};

export interface CreateAnalysisInput {
  projectId: string;
  name: string;
  area: AnalysisArea;
}

/** Analysis lifecycle + job calls (code-architecture §4 #7-#9, #14-#15). */
export const analysesApi = {
  async listForProject(
    projectId: string,
    params: ListAnalysesParams = {},
    signal?: AbortSignal,
  ): Promise<AnalysisList> {
    const query: QueryParams = {};
    if (params.ordering !== undefined) query.ordering = params.ordering;
    if (params.page !== undefined) query.page = params.page;
    const data = await http.get(`/projects/${projectId}/analyses/`, {
      params: query,
      ...(signal ? { signal } : {}),
    });
    return parseResponse(analysisListSchema, data);
  },

  async get(analysisId: string, signal?: AbortSignal): Promise<AnalysisDetail> {
    const data = await http.get(`/analyses/${analysisId}/`, {
      ...(signal ? { signal } : {}),
    });
    return parseResponse(analysisDetailSchema, data);
  },

  async create(input: CreateAnalysisInput): Promise<Analysis> {
    const data = await http.post(`/projects/${input.projectId}/analyses/`, {
      body: { name: input.name, area: input.area },
    });
    return parseResponse(analysisSchema, data);
  },

  /** Submit for processing; the required Idempotency-Key header is generated here. */
  async submit(analysisId: string): Promise<SubmitResponse> {
    const data = await http.post(`/analyses/${analysisId}/submit/`, {
      body: {},
      headers: { 'Idempotency-Key': generateIdempotencyKey() },
    });
    return parseResponse(submitResponseSchema, data);
  },

  async getJob(analysisId: string, signal?: AbortSignal): Promise<Job> {
    const data = await http.get(`/analyses/${analysisId}/job/`, {
      ...(signal ? { signal } : {}),
    });
    return parseResponse(jobSchema, data);
  },

  async cancelJob(analysisId: string): Promise<Job> {
    const data = await http.post(`/analyses/${analysisId}/job/cancel/`, { body: {} });
    return parseResponse(jobSchema, data);
  },
};
