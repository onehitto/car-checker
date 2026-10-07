import { createBrowserRouter } from "react-router";

import { AuthLayout } from "@/features/auth/AuthLayout";
import { RedirectIfSignedIn, RequireAuth } from "@/features/auth/guards";
import { AppShell } from "@/features/layout/AppShell";
import { NotFoundPage } from "@/features/layout/NotFoundPage";
import { RouteError } from "@/features/layout/RouteError";

/** Each screen is a lazily loaded chunk. */
export const router = createBrowserRouter([
  {
    errorElement: <RouteError />,
    children: [
      {
        element: <RedirectIfSignedIn />,
        children: [
          {
            element: <AuthLayout />,
            children: [
              {
                path: "/login",
                lazy: async () => ({
                  Component: (await import("@/features/auth/LoginPage")).LoginPage,
                }),
              },
              {
                path: "/register",
                lazy: async () => ({
                  Component: (await import("@/features/auth/RegisterPage")).RegisterPage,
                }),
              },
              {
                path: "/forgot-password",
                lazy: async () => ({
                  Component: (await import("@/features/auth/ForgotPasswordPage"))
                    .ForgotPasswordPage,
                }),
              },
            ],
          },
        ],
      },
      {
        element: <AuthLayout />,
        children: [
          {
            path: "/reset-password",
            lazy: async () => ({
              Component: (await import("@/features/auth/ResetPasswordPage")).ResetPasswordPage,
            }),
          },
        ],
      },
      {
        element: <RequireAuth />,
        children: [
          {
            element: <AppShell />,
            errorElement: <RouteError />,
            children: [
              {
                index: true,
                lazy: async () => ({
                  Component: (await import("@/features/dashboard/DashboardPage")).DashboardPage,
                }),
              },
              { path: "*", element: <NotFoundPage /> },
            ],
          },
        ],
      },
    ],
  },
]);
