import { z } from 'zod';

export const projectSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string().nullable().default(null),
  is_archived: z.boolean(),
  created_at: z.string().datetime({ offset: true }),
  updated_at: z.string().datetime({ offset: true }),
});

/** DRF page-number pagination envelope, parameterized by row schema. */
export function paginatedSchema<TItem extends z.ZodTypeAny>(item: TItem) {
  return z.object({
    count: z.number().int().nonnegative(),
    next: z.string().url().nullable(),
    previous: z.string().url().nullable(),
    results: z.array(item),
  });
}

export const projectListSchema = paginatedSchema(projectSchema);

export const createProjectInputSchema = z.object({
  name: z
    .string()
    .min(1, 'Project name is required')
    .max(120, 'Project name must be 120 characters or fewer'),
  description: z.string().max(2000, 'Description is too long').optional(),
});

export type Project = z.infer<typeof projectSchema>;
export type ProjectList = z.infer<typeof projectListSchema>;
export type CreateProjectInput = z.infer<typeof createProjectInputSchema>;
