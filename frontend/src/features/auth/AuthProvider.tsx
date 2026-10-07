import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";

import { api, expectNoContent } from "@/api/client";
import { session } from "@/api/session";
import type { AuthResult } from "@/api/types";
import { isLanguage, setLanguage } from "@/i18n";

import { AuthContext, type AuthContextValue, type AuthStatus } from "./authContext";
import { fetchMe, ME_QUERY_KEY } from "./meQuery";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthStatus>(() =>
    session.hasRefreshToken() ? "loading" : "signedOut",
  );

  // Resume a stored session on load (one shared refresh even under StrictMode).
  useEffect(() => {
    if (!session.hasRefreshToken()) return;
    void session.refresh().then((ok) => setStatus(ok ? "signedIn" : "signedOut"));
  }, []);

  useEffect(
    () =>
      session.subscribe((signedIn) => {
        setStatus(signedIn ? "signedIn" : "signedOut");
        if (!signedIn) queryClient.clear();
      }),
    [queryClient],
  );

  const me = useQuery({ queryKey: ME_QUERY_KEY, queryFn: fetchMe, enabled: status === "signedIn" });

  useEffect(() => {
    const language = me.data?.preferred_language;
    if (isLanguage(language)) void setLanguage(language);
  }, [me.data?.preferred_language]);

  const signIn = useCallback(
    (result: AuthResult) => {
      queryClient.setQueryData(ME_QUERY_KEY, result.user);
      session.setTokens(result.tokens);
    },
    [queryClient],
  );

  const signOut = useCallback(async () => {
    try {
      await expectNoContent(api.POST("/api/v1/auth/logout"));
    } catch {
      // The session ends locally even if the server cannot be reached.
    }
    session.clear();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user: me.data, signIn, signOut }),
    [status, me.data, signIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
