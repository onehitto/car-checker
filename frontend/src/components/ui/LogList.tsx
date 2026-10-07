import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** History reads like a logbook: one ruled line per entry. */
export function LogList({ children, className }: { children: ReactNode; className?: string }) {
  return <ul className={cn("divide-y divide-rule", className)}>{children}</ul>;
}

interface LogRowProps {
  date?: ReactNode;
  mileage?: ReactNode;
  title: ReactNode;
  details?: ReactNode;
  amount?: ReactNode;
  actions?: ReactNode;
}

/**
 * Dated entry: date | mileage | what | amount | menu. On phones, date and mileage share the
 * first line and the amount sits under the menu.
 */
export function LogRow({ date, mileage, title, details, amount, actions }: LogRowProps) {
  return (
    <li
      className={cn(
        "grid grid-cols-[auto_minmax(0,1fr)_auto] items-baseline gap-x-4 gap-y-0.5 py-3",
        "[grid-template-areas:'date_mileage_actions'_'what_what_amount']",
        "sm:grid-cols-[7.5rem_7rem_minmax(0,1fr)_auto_2rem]",
        "sm:[grid-template-areas:'date_mileage_what_amount_actions']",
      )}
    >
      <span className="text-sm text-steel numeric [grid-area:date] sm:text-[15px] sm:text-ink">
        {date}
      </span>
      <span className="text-sm text-steel numeric [grid-area:mileage] sm:text-[15px]">
        {mileage}
      </span>
      <div className="min-w-0 [grid-area:what]">
        <div className="font-medium">{title}</div>
        {details && <div className="text-sm text-steel">{details}</div>}
      </div>
      <span className="text-end font-medium numeric [grid-area:amount]">{amount}</span>
      <span className="self-center justify-self-end [grid-area:actions]">{actions}</span>
    </li>
  );
}

/** Undated entry (schedules, documents, tires): what | status | menu. */
export function ItemRow({
  title,
  details,
  aside,
  actions,
  lead,
}: {
  title: ReactNode;
  details?: ReactNode;
  aside?: ReactNode;
  actions?: ReactNode;
  lead?: ReactNode;
}) {
  return (
    <li className="flex items-center gap-3 py-3">
      {lead}
      <div className="min-w-0 flex-1">
        <div className="font-medium">{title}</div>
        {details && <div className="text-sm text-steel">{details}</div>}
      </div>
      {aside && <div className="flex shrink-0 flex-col items-end gap-1 text-end">{aside}</div>}
      {actions && <div className="w-8 shrink-0">{actions}</div>}
    </li>
  );
}
