import { http, parseResponse } from '@/api';
import {
  tokenPairSchema,
  accessTokenSchema,
  userSchema,
  type LoginInput,
  type RegisterPayload,
  type TokenPair,
  type AccessTokenResponse,
  type User,
} from '@/schemas';

/**
 * Auth endpoint calls (code-architecture.md §4, rows 1-4). Pure request
 * functions — no React, no token storage. The auth hook orchestrates storage.
 */
export const authApi = {
  async login(input: LoginInput): Promise<TokenPair> {
    const data = await http.post('/auth/login/', { body: input, skipAuth: true });
    return parseResponse(tokenPairSchema, data);
  },

  async register(payload: RegisterPayload): Promise<User> {
    const data = await http.post('/auth/register/', { body: payload, skipAuth: true });
    return parseResponse(userSchema, data);
  },

  async refresh(refreshToken: string): Promise<AccessTokenResponse> {
    const data = await http.post('/auth/refresh/', {
      body: { refresh: refreshToken },
      skipAuth: true,
    });
    return parseResponse(accessTokenSchema, data);
  },

  async me(): Promise<User> {
    const data = await http.get('/me/');
    return parseResponse(userSchema, data);
  },
};
