import { useTranslation } from "react-i18next";

import { ButtonLink, EmptyState } from "@/components/ui";

export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <EmptyState
      title={t("errors.notFoundTitle")}
      body={t("errors.notFound")}
      action={<ButtonLink to="/">{t("nav.dashboard")}</ButtonLink>}
    />
  );
}
