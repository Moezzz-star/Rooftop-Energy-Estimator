import { http, parseResponse, type QueryParams } from '@/api';
import {
  projectListSchema,
  projectSchema,
  type CreateProjectInput,
  type Project,
  type ProjectList,
} from '@/schemas';

export type ListProjectsParams = {
  name?: string;
  archived?: boolean;
  ordering?: string;
  page?: number;
};

/** Project resource calls (code-architecture.md §4, rows 5-6). */
export const projectsApi = {
  async list(params: ListProjectsParams, signal?: AbortSignal): Promise<ProjectList> {
    const query: QueryParams = {};
    if (params.name !== undefined) query.name = params.name;
    if (params.archived !== undefined) query.archived = params.archived;
    if (params.ordering !== undefined) query.ordering = params.ordering;
    if (params.page !== undefined) query.page = params.page;
    const data = await http.get('/projects/', {
      params: query,
      ...(signal ? { signal } : {}),
    });
    return parseResponse(projectListSchema, data);
  },

  async create(input: CreateProjectInput): Promise<Project> {
    const data = await http.post('/projects/', { body: input });
    return parseResponse(projectSchema, data);
  },
};
