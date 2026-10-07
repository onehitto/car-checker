import { useTranslation } from "react-i18next";
import { isRouteErrorResponse, useRouteError } from "react-router";

import { ButtonLink, ErrorState } from "@/components/ui";

/** Shown when a page crashes or a lazy chunk fails to load. */
export function RouteError() {
  const { t } = useTranslation();
  const error = useRouteError();
  if (isRouteErrorResponse(error) && error.status === 404) {
    return <p className="p-8">{t("errors.notFound")}</p>;
  }
  return (
    <div className="p-8">
      <ErrorState error={error} onRetry={() => window.location.reload()} />
      <ButtonLink to="/">{t("nav.dashboard")}</ButtonLink>
    </div>
  );
}
