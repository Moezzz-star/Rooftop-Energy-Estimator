/**
 * Decouples the HTTP client from the auth context. `useAuth` registers the
 * current access token and a refresh handler here; the HTTP client reads the
 * token for the Authorization header and calls `refresh()` on a 401.
 *
 * This avoids a circular import between the client and the auth provider while
 * keeping token storage rules (access in memory, refresh in localStorage)
 * entirely inside the auth layer.
 */
type RefreshHandler = () => Promise<string | null>;

let accessToken: string | null = null;
let refreshHandler: RefreshHandler | null = null;
let inFlightRefresh: Promise<string | null> | null = null;

export const authBridge = {
  getAccessToken(): string | null {
    return accessToken;
  },
  setAccessToken(token: string | null): void {
    accessToken = token;
  },
  setRefreshHandler(handler: RefreshHandler | null): void {
    refreshHandler = handler;
  },
  /**
   * Runs the registered refresh handler, coalescing concurrent 401s into a
   * single refresh request. Resolves to the new access token or null.
   */
  async refresh(): Promise<string | null> {
    if (!refreshHandler) return null;
    if (!inFlightRefresh) {
      inFlightRefresh = refreshHandler().finally(() => {
        inFlightRefresh = null;
      });
    }
    return inFlightRefresh;
  },
};
