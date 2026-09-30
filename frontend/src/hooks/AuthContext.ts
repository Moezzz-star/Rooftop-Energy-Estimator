import { createContext, useContext } from 'react';
import type { LoginInput, RegisterInput, User } from '@/schemas';

export const REFRESH_TOKEN_STORAGE_KEY = 'ree-refresh-token';

export interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  /** True while the session is being restored on first load. */
  isBootstrapping: boolean;
  login: (input: LoginInput) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}

export const refreshTokenStore = {
  get(): string | null {
    if (typeof window === 'undefined') return null;
    return window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
  },
  set(token: string): void {
    window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
  },
  clear(): void {
    window.localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
  },
};
