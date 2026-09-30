import { z } from 'zod';

export const userSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  is_active: z.boolean(),
  date_joined: z.string().datetime({ offset: true }),
});

export type User = z.infer<typeof userSchema>;
