import type { ComponentType } from "react";
import { createBrowserRouter } from "react-router";

import { AuthLayout } from "@/features/auth/AuthLayout";
import { RedirectIfSignedIn, RequireAuth } from "@/features/auth/guards";
import { AppShell } from "@/features/layout/AppShell";
import { NotFoundPage } from "@/features/layout/NotFoundPage";
import { RouteError } from "@/features/layout/RouteError";

/** Each screen is a lazily loaded chunk. */
function page<M>(load: () => Promise<M>, pick: (module: M) => ComponentType) {
  return async () => ({ Component: pick(await load()) });
}

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
                lazy: page(
                  () => import("@/features/auth/LoginPage"),
                  (m) => m.LoginPage,
                ),
              },
              {
                path: "/register",
                lazy: page(
                  () => import("@/features/auth/RegisterPage"),
                  (m) => m.RegisterPage,
                ),
              },
              {
                path: "/forgot-password",
                lazy: page(
                  () => import("@/features/auth/ForgotPasswordPage"),
                  (m) => m.ForgotPasswordPage,
                ),
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
            lazy: page(
              () => import("@/features/auth/ResetPasswordPage"),
              (m) => m.ResetPasswordPage,
            ),
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
                lazy: page(
                  () => import("@/features/dashboard/DashboardPage"),
                  (m) => m.DashboardPage,
                ),
              },
              {
                path: "vehicles",
                lazy: page(
                  () => import("@/features/vehicles/VehiclesPage"),
                  (m) => m.VehiclesPage,
                ),
              },
              {
                path: "vehicles/new",
                lazy: page(
                  () => import("@/features/vehicles/VehicleFormPage"),
                  (m) => m.VehicleFormPage,
                ),
              },
              {
                path: "vehicles/:vehicleId/edit",
                lazy: page(
                  () => import("@/features/vehicles/VehicleFormPage"),
                  (m) => m.VehicleFormPage,
                ),
              },
              {
                path: "vehicles/:vehicleId",
                lazy: page(
                  () => import("@/features/vehicles/VehicleLayout"),
                  (m) => m.VehicleLayout,
                ),
                children: vehicleTabs(),
              },
              {
                path: "statistics",
                lazy: page(
                  () => import("@/features/statistics/StatisticsPage"),
                  (m) => m.StatisticsPage,
                ),
              },
              { path: "*", element: <NotFoundPage /> },
            ],
          },
        ],
      },
    ],
  },
]);

/** Tabs of a vehicle page; each tab may hold sections (secondary tabs). */
function vehicleTabs() {
  return [
    {
      index: true,
      lazy: page(
        () => import("@/features/vehicles/OverviewTab"),
        (m) => m.OverviewTab,
      ),
    },
    {
      path: "maintenance",
      lazy: page(
        () => import("@/features/maintenance/MaintenanceSection"),
        (m) => m.MaintenanceSection,
      ),
      children: [
        {
          index: true,
          lazy: page(
            () => import("@/features/maintenance/RecordsTab"),
            (m) => m.RecordsTab,
          ),
        },
        {
          path: "schedules",
          lazy: page(
            () => import("@/features/maintenance/SchedulesTab"),
            (m) => m.SchedulesTab,
          ),
        },
        {
          path: "oil-changes",
          lazy: page(
            () => import("@/features/maintenance/OilChangesTab"),
            (m) => m.OilChangesTab,
          ),
        },
      ],
    },
    {
      path: "mileage",
      lazy: page(
        () => import("@/features/mileage/MileageSection"),
        (m) => m.MileageSection,
      ),
      children: [
        {
          index: true,
          lazy: page(
            () => import("@/features/mileage/MileageTab"),
            (m) => m.MileageTab,
          ),
        },
        {
          path: "fuel",
          lazy: page(
            () => import("@/features/fuel/FuelTab"),
            (m) => m.FuelTab,
          ),
        },
      ],
    },
    {
      path: "expenses",
      lazy: page(
        () => import("@/features/expenses/CostsSection"),
        (m) => m.CostsSection,
      ),
      children: [
        {
          index: true,
          lazy: page(
            () => import("@/features/expenses/ExpensesTab"),
            (m) => m.ExpensesTab,
          ),
        },
        {
          path: "statistics",
          lazy: page(
            () => import("@/features/statistics/VehicleStatisticsTab"),
            (m) => m.VehicleStatisticsTab,
          ),
        },
      ],
    },
    {
      path: "documents",
      lazy: page(
        () => import("@/features/documents/DocumentsSection"),
        (m) => m.DocumentsSection,
      ),
      children: [
        {
          index: true,
          lazy: page(
            () => import("@/features/documents/DocumentsTab"),
            (m) => m.DocumentsTab,
          ),
        },
        {
          path: "files",
          lazy: page(
            () => import("@/features/attachments/FilesTab"),
            (m) => m.FilesTab,
          ),
        },
      ],
    },
  ];
}
