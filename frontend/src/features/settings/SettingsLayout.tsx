import { useTranslation } from "react-i18next";
import { Outlet } from "react-router";

import { PageHeader, TabNav } from "@/components/ui";

export function SettingsLayout() {
  const { t } = useTranslation();
  return (
    <>
      <PageHeader title={t("settings.title")} />
      <div className="flex flex-col gap-6">
        <TabNav
          variant="secondary"
          label={t("settings.title")}
          items={[
            { to: "/settings", label: t("settings.sections.profile"), end: true },
            { to: "/settings/security", label: t("settings.sections.security") },
            { to: "/settings/notifications", label: t("settings.sections.notifications") },
            { to: "/settings/types", label: t("settings.sections.types") },
            { to: "/settings/account", label: t("settings.sections.account") },
          ]}
        />
        <Outlet />
      </div>
    </>
  );
}
