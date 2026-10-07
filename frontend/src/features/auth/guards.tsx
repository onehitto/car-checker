import { Navigate, Outlet, useLocation } from "react-router";

import { LoadingState } from "@/components/ui";

import { useAuth } from "./authContext";

/** Signed-in area: waits for the session and the profile, else sends to the sign-in page. */
export function RequireAuth() {
  const { status, user } = useAuth();
  const location = useLocation();
  if (status === "signedOut") {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  if (status === "loading" || !user) {
    return (
      <div className="grid min-h-dvh place-items-center">
        <LoadingState />
      </div>
    );
  }
  return <Outlet />;
}

/** Sign-in pages: already signed-in users go straight to the app. */
export function RedirectIfSignedIn() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "signedIn") {
    const next = new URLSearchParams(location.search).get("next");
    return <Navigate to={next?.startsWith("/") ? next : "/"} replace />;
  }
  if (status === "loading") {
    return (
      <div className="grid min-h-dvh place-items-center">
        <LoadingState />
      </div>
    );
  }
  return <Outlet />;
}
