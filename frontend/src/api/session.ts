/** Token storage. The access token stays in memory; the refresh token is persisted so the
 * user stays signed in across reloads. Concurrent refreshes share one request. */

const REFRESH_TOKEN_KEY = "car-checker.refresh-token";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

type Listener = (signedIn: boolean) => void;

let accessToken: string | null = null;
let pendingRefresh: Promise<boolean> | null = null;
const listeners = new Set<Listener>();

function readRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeRefreshToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(REFRESH_TOKEN_KEY, token);
    else localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {
    // Storage unavailable (private mode): the session lasts until the tab closes.
  }
}

function notify(signedIn: boolean): void {
  listeners.forEach((listener) => listener(signedIn));
}

async function requestRefresh(token: string): Promise<boolean> {
  let response: Response;
  try {
    response = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token }),
    });
  } catch {
    return false; // offline: keep the stored token and try again later
  }
  if (!response.ok) {
    session.clear();
    return false;
  }
  const body = (await response.json()) as { data: TokenPair };
  session.setTokens(body.data);
  return true;
}

export const session = {
  getAccessToken(): string | null {
    return accessToken;
  },

  hasRefreshToken(): boolean {
    return readRefreshToken() !== null;
  },

  setTokens(tokens: TokenPair): void {
    accessToken = tokens.access_token;
    writeRefreshToken(tokens.refresh_token);
    notify(true);
  },

  clear(): void {
    accessToken = null;
    writeRefreshToken(null);
    notify(false);
  },

  /** Exchange the stored refresh token for a new pair. Resolves to false when signed out. */
  refresh(): Promise<boolean> {
    const token = readRefreshToken();
    if (!token) return Promise.resolve(false);
    pendingRefresh ??= requestRefresh(token).finally(() => {
      pendingRefresh = null;
    });
    return pendingRefresh;
  },

  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};
