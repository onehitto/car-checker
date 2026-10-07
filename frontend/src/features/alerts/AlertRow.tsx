import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { Alert } from "@/api/types";
import { StatusBadge, toneFor } from "@/components/ui";
import { cn } from "@/lib/cn";
import { useFormat } from "@/lib/useFormat";

const LAMPS = {
  ok: "bg-ok",
  upcoming: "bg-upcoming",
  soon: "bg-soon",
  due: "bg-due",
  overdue: "bg-overdue",
  neutral: "bg-steel",
} as const;

interface AlertRowProps {
  alert: Alert;
  /** Title and date only (side panels). */
  compact?: boolean;
  vehicleName?: string;
  actions?: ReactNode;
}

/** One alert: priority lamp, title, message; unread alerts are set in bold. */
export function AlertRow({ alert, compact, vehicleName, actions }: AlertRowProps) {
  const { t } = useTranslation();
  const format = useFormat();
  const unread = alert.status === "active";
  return (
    <li className="flex items-start gap-3 py-3">
      <span
        aria-hidden="true"
        className={cn("mt-2 size-2 shrink-0 rounded-full", LAMPS[toneFor(alert.priority)])}
      />
      <div className="min-w-0 flex-1">
        <p className={cn(unread ? "font-semibold" : "font-medium text-ink/80")}>
          {unread && <span className="sr-only">{t("alerts.unread")}: </span>}
          {alert.title}
        </p>
        {!compact && <p className="text-sm text-steel">{alert.message}</p>}
        <p className="mt-0.5 flex flex-wrap gap-x-3 text-sm text-steel">
          {vehicleName && <span>{vehicleName}</span>}
          <span className="numeric">{format.date(alert.created_at)}</span>
          {!unread && <span>{t(`enums.alertStatus.${alert.status}`)}</span>}
        </p>
      </div>
      {!compact && <StatusBadge status={alert.priority} />}
      {actions}
    </li>
  );
}
