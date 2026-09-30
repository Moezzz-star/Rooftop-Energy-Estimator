/**
 * Centralized TanStack Query keys. Feature hooks import from here so cache
 * invalidation stays consistent across slices (see §5 — cache keyed by resource).
 */
export const queryKeys = {
  me: ['me'] as const,
  projects: {
    all: ['projects'] as const,
    list: (params?: Record<string, unknown>) => ['projects', 'list', params ?? {}] as const,
    detail: (id: string) => ['projects', 'detail', id] as const,
  },
  analyses: {
    all: ['analyses'] as const,
    listForProject: (projectId: string) => ['analyses', 'project', projectId] as const,
    detail: (id: string) => ['analyses', 'detail', id] as const,
    job: (id: string) => ['analyses', id, 'job'] as const,
    results: (id: string) => ['analyses', id, 'results'] as const,
    buildings: (id: string, params?: Record<string, unknown>) =>
      ['analyses', id, 'buildings', params ?? {}] as const,
    features: (id: string, params?: Record<string, unknown>) =>
      ['analyses', id, 'features', params ?? {}] as const,
  },
  buildings: {
    detail: (id: string) => ['buildings', 'detail', id] as const,
  },
} as const;
