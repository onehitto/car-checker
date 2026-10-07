import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

import { type Tone, toneFor } from "./tones";

const TONES: Record<Tone, string> = {
  ok: "bg-ok-soft text-ok",
  upcoming: "bg-upcoming-soft text-upcoming",
  soon: "bg-soon-soft text-[#8a5a12]",
  due: "bg-due-soft text-due",
  overdue: "bg-overdue-soft text-overdue",
  neutral: "bg-paper text-steel",
};

const LAMPS: Record<Tone, string> = {
  ok: "bg-ok",
  upcoming: "bg-upcoming",
  soon: "bg-soon",
  due: "bg-due",
  overdue: "bg-overdue",
  neutral: "bg-steel",
};

export function Badge({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[13px] font-medium whitespace-nowrap",
        TONES[tone],
      )}
    >
      <span aria-hidden="true" className={cn("size-1.5 rounded-full", LAMPS[tone])} />
      {children}
    </span>
  );
}

/** Maintenance, document, part or alert status rendered with its translated label. */
export function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  return (
    <Badge tone={toneFor(status)}>
      {t(`status.${status}` as "status.ok", { defaultValue: status })}
    </Badge>
  );
}
