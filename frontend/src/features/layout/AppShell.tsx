import * as RadixDialog from "@radix-ui/react-dialog";
import { Bell, Menu } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Outlet } from "react-router";

import { useAlertSummary } from "@/features/alerts/queries";

import { Sidebar } from "./Sidebar";

export function AppShell() {
  const { t } = useTranslation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const alerts = useAlertSummary();
  const unread = alerts.data?.unread ?? 0;

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[256px_minmax(0,1fr)]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:start-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-sheet focus:px-3 focus:py-2"
      >
        {t("nav.skipToContent")}
      </a>

      <div className="sticky top-0 hidden h-dvh lg:block">
        <Sidebar />
      </div>

      <header className="sticky top-0 z-30 flex items-center justify-between bg-ink px-4 py-3 text-white lg:hidden">
        <RadixDialog.Root open={drawerOpen} onOpenChange={setDrawerOpen}>
          <RadixDialog.Trigger
            className="rounded-md p-1.5 hover:bg-ink-soft"
            aria-label={t("common.openMenu")}
          >
            <Menu className="size-6" />
          </RadixDialog.Trigger>
          <RadixDialog.Portal>
            <RadixDialog.Overlay className="fixed inset-0 z-40 bg-ink/60" />
            <RadixDialog.Content className="fixed inset-y-0 start-0 z-50 w-72 max-w-[85vw] focus:outline-none">
              <RadixDialog.Title className="sr-only">{t("nav.main")}</RadixDialog.Title>
              <RadixDialog.Description className="sr-only">{t("nav.main")}</RadixDialog.Description>
              <Sidebar onNavigate={() => setDrawerOpen(false)} />
            </RadixDialog.Content>
          </RadixDialog.Portal>
        </RadixDialog.Root>
        <Link to="/" className="font-display text-xl font-bold">
          {t("app.name")}
        </Link>
        <Link
          to="/alerts"
          className="relative rounded-md p-1.5 hover:bg-ink-soft"
          aria-label={t("nav.alerts")}
        >
          <Bell className="size-6" />
          {unread > 0 && (
            <span className="absolute -end-0.5 -top-0.5 rounded-full bg-overdue px-1 text-[11px] font-semibold numeric">
              {unread}
            </span>
          )}
        </Link>
      </header>

      <main id="main" className="mx-auto w-full max-w-[1200px] px-4 py-6 sm:px-8 sm:py-8">
        <Outlet />
      </main>
    </div>
  );
}
