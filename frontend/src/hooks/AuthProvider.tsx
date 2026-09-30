import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { authBridge } from '@/api';
import { authApi } from '@/features/auth/api';
import type { LoginInput, RegisterInput, User } from '@/schemas';
import { AuthContext, refreshTokenStore, type AuthContextValue } from './AuthContext';

/**
 * Owns the session. Access token lives in memory (via `authBridge`); the
 * refresh token is persisted in localStorage. Registers a refresh handler so
 * the HTTP client can transparently refresh + retry on a 401.
 */
export function AuthProvider({ children }: { children: ReactNode }): JSX.Element {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState<boolean>(true);
  // Guard against setState after unmount during async bootstrap.
  const mountedRef = useRef(true);

  const clearSession = useCallback((): void => {
    authBridge.setAccessToken(null);
    refreshTokenStore.clear();
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  // Register the refresh handler used by the HTTP client on a 401.
  useEffect(() => {
    authBridge.setRefreshHandler(async () => {
      const refreshToken = refreshTokenStore.get();
      if (!refreshToken) return null;
      try {
        const tokens = await authApi.refresh(refreshToken);
        authBridge.setAccessToken(tokens.access);
        if (tokens.refresh) refreshTokenStore.set(tokens.refresh);
        return tokens.access;
      } catch {
        clearSession();
        return null;
      }
    });
    return () => authBridge.setRefreshHandler(null);
  }, [clearSession]);

  // Restore session on first load if a refresh token is present.
  useEffect(() => {
    mountedRef.current = true;
    const bootstrap = async (): Promise<void> => {
      const refreshToken = refreshTokenStore.get();
      if (!refreshToken) {
        if (mountedRef.current) setIsBootstrapping(false);
        return;
      }
      try {
        const tokens = await authApi.refresh(refreshToken);
        authBridge.setAccessToken(tokens.access);
        if (tokens.refresh) refreshTokenStore.set(tokens.refresh);
        const me = await authApi.me();
        if (mountedRef.current) setUser(me);
      } catch {
        clearSession();
      } finally {
        if (mountedRef.current) setIsBootstrapping(false);
      }
    };
    void bootstrap();
    return () => {
      mountedRef.current = false;
    };
  }, [clearSession]);

  const login = useCallback(async (input: LoginInput): Promise<void> => {
    const tokens = await authApi.login(input);
    authBridge.setAccessToken(tokens.access);
    refreshTokenStore.set(tokens.refresh);
    const me = await authApi.me();
    setUser(me);
  }, []);

  const register = useCallback(
    async (input: RegisterInput): Promise<void> => {
      await authApi.register({ email: input.email, password: input.password });
      await login({ email: input.email, password: input.password });
    },
    [login],
  );

  const logout = useCallback((): void => {
    clearSession();
  }, [clearSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isBootstrapping,
      login,
      register,
      logout,
    }),
    [user, isBootstrapping, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
