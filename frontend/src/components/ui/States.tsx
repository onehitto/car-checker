import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { isApiError } from "@/api/errors";

import { Button, Spinner } from "./Button";
import { errorMessage } from "./errorMessage";

export function LoadingState({ label }: { label?: string }) {
  const { t } = useTranslation();
  return (
    <div role="status" className="flex items-center gap-2 py-10 text-steel">
      <Spinner />
      {label ?? t("common.loading")}
    </div>
  );
}

/** Empty lists invite the next action. */
export function EmptyState({
  title,
  body,
  action,
}: {
  title: ReactNode;
  body?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-3 py-8">
      <p className="font-display text-xl font-semibold">{title}</p>
      {body && <p className="max-w-prose text-steel">{body}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation();
  const requestId = isApiError(error) ? error.requestId : null;
  return (
    <div role="alert" className="flex flex-col items-start gap-3 py-8">
      <p className="text-overdue">{errorMessage(error, t)}</p>
      {requestId && (
        <p className="text-sm text-steel">{t("errors.requestId", { id: requestId })}</p>
      )}
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          {t("common.retry")}
        </Button>
      )}
    </div>
  );
}
