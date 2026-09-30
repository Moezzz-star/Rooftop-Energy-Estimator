import { z } from 'zod';
import { http, parseResponse } from '@/api';

/** One imagery provider capability row from GET /imagery/sources/. */
export const imagerySourceSchema = z.object({
  name: z.string(),
  title: z.string(),
  description: z.string(),
  supports_upload: z.boolean(),
  supports_windowed_read: z.boolean().optional(),
  requires_network: z.boolean().optional(),
  available: z.boolean().optional(),
});
export type ImagerySource = z.infer<typeof imagerySourceSchema>;

/** The endpoint wraps the list in `{ sources: [...] }`. */
const imagerySourcesResponseSchema = z.object({
  sources: z.array(imagerySourceSchema),
});

export const imageryApi = {
  async listSources(signal?: AbortSignal): Promise<ImagerySource[]> {
    const data = await http.get('/imagery/sources/', { ...(signal ? { signal } : {}) });
    return parseResponse(imagerySourcesResponseSchema, data).sources;
  },
};
