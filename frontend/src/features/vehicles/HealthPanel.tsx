import { useTranslation } from "react-i18next";

import type { VehicleDashboard } from "@/api/types";
import { Badge, Panel, type Tone } from "@/components/ui";
import { cn } from "@/lib/cn";

type Health = VehicleDashboard["health"];

const LEVEL_TONES: Record<Health["level"], Tone> = {
  good: "ok",
  attention: "soon",
  critical: "overdue",
};

const SEGMENT_COLORS: Record<Tone, string> = {
  ok: "bg-ok",
  upcoming: "bg-upcoming",
  soon: "bg-soon",
  due: "bg-due",
  overdue: "bg-overdue",
  neutral: "bg-steel",
};

const SEGMENTS = 10;

/** Condition score drawn as a segmented gauge, with the warning lamps that lower it. */
export function HealthPanel({ health }: { health: Health }) {
  const { t } = useTranslation();
  const tone = LEVEL_TONES[health.level];
  const filled = Math.round((health.score / 100) * SEGMENTS);
  const lamps: { count: number; label: string; tone: Tone }[] = [
    {
      count: health.overdue_maintenance,
      label: t("health.overdueMaintenance", { count: health.overdue_maintenance }),
      tone: "overdue",
    },
    {
      count: health.due_maintenance,
      label: t("health.dueMaintenance", { count: health.due_maintenance }),
      tone: "due",
    },
    {
      count: health.expired_documents,
      label: t("health.expiredDocuments", { count: health.expired_documents }),
      tone: "overdue",
    },
    {
      count: health.expiring_documents,
      label: t("health.expiringDocuments", { count: health.expiring_documents }),
      tone: "soon",
    },
    {
      count: health.worn_parts,
      label: t("health.wornParts", { count: health.worn_parts }),
      tone: "due",
    },
  ];
  const lit = lamps.filter((lamp) => lamp.count > 0);

  return (
    <Panel title={t("health.title")} bodyClassName="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <Badge tone={tone}>{t(`health.level.${health.level}`)}</Badge>
        <span className="font-display text-2xl font-semibold numeric">
          {health.score}
          <span className="text-base text-steel">/100</span>
        </span>
      </div>
      <div
        role="meter"
        aria-label={t("health.title")}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={health.score}
        className="flex gap-1"
        dir="ltr"
      >
        {Array.from({ length: SEGMENTS }, (_, index) => (
          <span
            key={index}
            className={cn(
              "h-2.5 flex-1 rounded-sm",
              index < filled ? SEGMENT_COLORS[tone] : "bg-rule",
            )}
          />
        ))}
      </div>
      {lit.length === 0 ? (
        <p className="text-sm text-steel">{t("health.allClear")}</p>
      ) : (
        <ul className="flex flex-col gap-1 text-sm">
          {lit.map((lamp) => (
            <li key={lamp.label} className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className={cn("size-2 rounded-full", SEGMENT_COLORS[lamp.tone])}
              />
              {lamp.label}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
