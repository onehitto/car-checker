import { useTranslation } from "react-i18next";

import { PageHeader } from "@/components/ui";
import { useCurrentUser } from "@/features/auth/authContext";

export function DashboardPage() {
  const { t } = useTranslation();
  const user = useCurrentUser();
  return <PageHeader title={t("dashboard.greeting", { name: user.first_name })} />;
}
