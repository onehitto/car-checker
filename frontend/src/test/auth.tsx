import type { ReactNode } from "react";

import type { User } from "@/api/types";
import { AuthContext } from "@/features/auth/authContext";

import { TEST_USER } from "./fixtures";

/** A signed-in user for components that read the profile (units, currency...). */
export function SignedIn({ user = TEST_USER, children }: { user?: User; children: ReactNode }) {
  return (
    <AuthContext.Provider
      value={{ status: "signedIn", user, signIn: () => {}, signOut: async () => {} }}
    >
      {children}
    </AuthContext.Provider>
  );
}
