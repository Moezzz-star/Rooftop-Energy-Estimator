import { z } from 'zod';

/** JWT pair returned by POST /auth/login/ and POST /auth/refresh/. */
export const tokenPairSchema = z.object({
  access: z.string().min(1),
  refresh: z.string().min(1),
});

/** Refresh endpoint may rotate only the access token. */
export const accessTokenSchema = z.object({
  access: z.string().min(1),
  refresh: z.string().min(1).optional(),
});

export const loginInputSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

export const registerInputSchema = z
  .object({
    email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

export type TokenPair = z.infer<typeof tokenPairSchema>;
export type AccessTokenResponse = z.infer<typeof accessTokenSchema>;
export type LoginInput = z.infer<typeof loginInputSchema>;
export type RegisterInput = z.infer<typeof registerInputSchema>;

/** Payload actually sent to POST /auth/register/ (confirmPassword is client-only). */
export type RegisterPayload = Pick<RegisterInput, 'email' | 'password'>;
