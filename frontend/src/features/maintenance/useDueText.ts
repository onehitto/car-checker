import { useCallback } from "react";
import { useTranslation } from "react-i18next";

import { useFormat } from "@/lib/useFormat";

/** Due state shared by schedules, parts lifetimes and reminders. */
export interface DueState {
  status: string;
  remaining_km?: number | null;
  remaining_days?: number | null;
  overdue_km?: number | null;
  overdue_days?: number | null;
}

/** "in 800 km or 15 days", "1,200 km and 25 days overdue", "Due now". */
export function useDueText() {
  const { t } = useTranslation();
  const format = useFormat();
  return useCallback(
    (item: DueState): string => {
      if (item.status === "unknown") return t("due.unknown");
      const days = (count: number) => t("due.days", { count });
      if (item.status === "overdue") {
        const km = item.overdue_km ?? negative(item.remaining_km);
        const late = item.overdue_days ?? negative(item.remaining_days);
        const parts = [km ? format.distance(km) : null, late ? days(late) : null];
        const amount = parts.filter(Boolean).join(t("due.and"));
        return amount ? t("due.overdueBy", { amount }) : t("status.overdue");
      }
      if (item.status === "due") return t("due.now");
      const parts = [
        item.remaining_km != null ? format.distance(Math.max(0, item.remaining_km)) : null,
        item.remaining_days != null ? days(Math.max(0, item.remaining_days)) : null,
      ];
      const amount = parts.filter(Boolean).join(t("due.or"));
      return amount ? t("due.in", { amount }) : "";
    },
    [t, format],
  );
}

function negative(value: number | null | undefined): number | null {
  return value != null && value < 0 ? -value : null;
}
