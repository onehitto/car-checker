import {
  Bell,
  CarFront,
  ChartColumn,
  LayoutDashboard,
  LogOut,
  Plus,
  Settings,
  Wrench,
} from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink } from "react-router";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/api/client";
import { useAlertSummary } from "@/features/alerts/queries";
import { useAuth } from "@/features/auth/authContext";
import { ME_QUERY_KEY } from "@/features/auth/meQuery";
import { useVehicleList } from "@/features/vehicles/queries";
import type { Language } from "@/i18n";
import { cn } from "@/lib/cn";
import { useFormat } from "@/lib/useFormat";

import { LanguageSwitcher } from "./LanguageSwitcher";

function NavItem({
  to,
  icon,
  children,
  end,
  onNavigate,
}: {
  to: string;
  icon: ReactNode;
  children: ReactNode;
  end?: boolean;
  onNavigate?: () => void;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-[15px] transition-colors",
          isActive
            ? "bg-ink-soft text-white"
            : "text-white/70 hover:bg-ink-soft/60 hover:text-white",
        )
      }
    >
      <span className="size-5 shrink-0 [&>svg]:size-5" aria-hidden="true">
        {icon}
      </span>
      <span className="flex flex-1 items-center justify-between gap-2">{children}</span>
    </NavLink>
  );
}

/** Instrument-cluster sidebar: navigation, the user's garage, account. */
export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation();
  const { user, signOut } = useAuth();
  const queryClient = useQueryClient();
  const format = useFormat();
  const vehicles = useVehicleList({ status: "active", limit: 100, sort: "created_at" });
  const alerts = useAlertSummary();
  const unread = alerts.data?.unread ?? 0;
  // The profile language is also used for alerts, e-mails and catalog names sent by the API.
  const saveLanguage = useMutation({
    mutationFn: (language: Language) =>
      unwrap(api.PATCH("/api/v1/users/me", { body: { preferred_language: language } })),
    onSuccess: (updated) => queryClient.setQueryData(ME_QUERY_KEY, updated),
  });

  return (
    <div className="flex h-full flex-col gap-6 bg-ink px-3 py-5 text-white">
      <Link to="/" onClick={onNavigate} className="px-3 font-display text-2xl font-bold">
        {t("app.name")}
      </Link>

      <nav aria-label={t("nav.main")} className="flex flex-col gap-0.5">
        <NavItem to="/" end icon={<LayoutDashboard />} onNavigate={onNavigate}>
          {t("nav.dashboard")}
        </NavItem>
        <NavItem to="/vehicles" end icon={<CarFront />} onNavigate={onNavigate}>
          {t("nav.vehicles")}
        </NavItem>
        <NavItem to="/alerts" icon={<Bell />} onNavigate={onNavigate}>
          {t("nav.alerts")}
          {unread > 0 && (
            <span className="rounded-full bg-overdue px-1.5 text-xs font-semibold text-white numeric">
              {unread}
              <span className="sr-only"> {t("nav.unread")}</span>
            </span>
          )}
        </NavItem>
        <NavItem to="/statistics" icon={<ChartColumn />} onNavigate={onNavigate}>
          {t("nav.statistics")}
        </NavItem>
        <NavItem to="/garages" icon={<Wrench />} onNavigate={onNavigate}>
          {t("nav.garages")}
        </NavItem>
        <NavItem to="/settings" icon={<Settings />} onNavigate={onNavigate}>
          {t("nav.settings")}
        </NavItem>
      </nav>

      <section aria-labelledby="garage-heading" className="flex min-h-0 flex-1 flex-col gap-1">
        <h2 id="garage-heading" className="px-3 text-sm font-medium text-white/50">
          {t("nav.myGarage")}
        </h2>
        <ul className="flex flex-col gap-0.5 overflow-y-auto">
          {vehicles.data?.items.map((vehicle) => (
            <li key={vehicle.id}>
              <NavLink
                to={`/vehicles/${vehicle.id}`}
                onClick={onNavigate}
                className={({ isActive }) =>
                  cn(
                    "flex flex-col rounded-md px-3 py-2 transition-colors",
                    isActive ? "bg-ink-soft" : "hover:bg-ink-soft/60",
                  )
                }
              >
                <span className="truncate text-[15px] text-white">{vehicle.display_name}</span>
                <span className="flex gap-3 text-sm text-white/50 numeric">
                  {format.distance(vehicle.current_mileage)}
                  {vehicle.license_plate && <span dir="ltr">{vehicle.license_plate}</span>}
                </span>
              </NavLink>
            </li>
          ))}
        </ul>
        <Link
          to="/vehicles/new"
          onClick={onNavigate}
          className="mt-1 flex items-center gap-2 rounded-md px-3 py-2 text-sm text-white/70 hover:bg-ink-soft/60 hover:text-white"
        >
          <Plus className="size-4" aria-hidden="true" />
          {t("nav.addVehicle")}
        </Link>
      </section>

      <div className="flex flex-col gap-3 border-t border-ink-line px-3 pt-4">
        <p className="truncate text-sm text-white/80">
          {user?.first_name} {user?.last_name}
        </p>
        <LanguageSwitcher
          className="text-white/80"
          onChange={(language) => saveLanguage.mutate(language)}
        />
        <button
          type="button"
          onClick={() => void signOut()}
          className="flex items-center gap-2 text-sm text-white/70 hover:text-white"
        >
          <LogOut className="size-4" aria-hidden="true" />
          {t("nav.signOut")}
        </button>
      </div>
    </div>
  );
}
