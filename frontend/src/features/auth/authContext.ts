import { createContext, useContext } from "react";

import type { AuthResult, User } from "@/api/types";

export type AuthStatus = "loading" | "signedIn" | "signedOut";

export interface AuthContextValue {
  status: AuthStatus;
  user: User | undefined;
  signIn: (result: AuthResult) => void;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}

/** The signed-in user; only call inside routes guarded by <RequireAuth>. */
export function useCurrentUser(): User {
  const { user } = useAuth();
  if (!user) throw new Error("useCurrentUser called outside an authenticated route");
  return user;
}
