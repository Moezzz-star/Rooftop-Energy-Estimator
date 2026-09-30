import { useQueryClient } from '@tanstack/react-query';
import { useApiQuery, useApiMutation, queryKeys } from '@/api';
import type { CreateProjectInput, Project, ProjectList } from '@/schemas';
import { projectsApi, type ListProjectsParams } from './api';

/** Query: paginated project list. */
export function useProjects(params: ListProjectsParams = {}) {
  return useApiQuery<ProjectList>({
    queryKey: queryKeys.projects.list(params),
    queryFn: (signal) => projectsApi.list(params, signal),
  });
}

/** Mutation: create a project, invalidating the list cache on success. */
export function useCreateProject() {
  const queryClient = useQueryClient();
  return useApiMutation<Project, CreateProjectInput>({
    mutationFn: (input) => projectsApi.create(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.projects.all }),
  });
}
