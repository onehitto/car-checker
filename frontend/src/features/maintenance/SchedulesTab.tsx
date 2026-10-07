import { useMutation } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent, unwrap } from "@/api/client";
import type { MaintenanceSchedule } from "@/api/types";
import {
  Badge,
  Button,
  EmptyState,
  errorMessage,
  ErrorState,
  ItemRow,
  LoadingState,
  Panel,
  RowMenu,
  StatusBadge,
  Toolbar,
  useToast,
} from "@/components/ui";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { useFormat } from "@/lib/useFormat";

import { useSchedules } from "./queries";
import { RecordFormDialog } from "./RecordFormDialog";
import { ScheduleFormDialog } from "./ScheduleFormDialog";
import { useDueText } from "./useDueText";

const SEVERITY = ["overdue", "due", "due_soon", "upcoming", "ok", "unknown"];

/** Maintenance plan: what is due when, from the last service and the intervals. */
export function SchedulesTab() {
  const { t } = useTranslation();
  const toast = useToast();
  const { vehicle, canEdit } = useVehicleContext();
  const schedules = useSchedules(vehicle.id);
  const [editing, setEditing] = useState<MaintenanceSchedule | "new" | null>(null);
  const [recording, setRecording] = useState<MaintenanceSchedule | null>(null);

  const remove = useConfirmDelete(
    (schedule: MaintenanceSchedule) =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/maintenance-schedules/{schedule_id}", {
          params: { path: { vehicle_id: vehicle.id, schedule_id: schedule.id } },
        }),
      ),
    { successMessage: t("schedules.deleted"), body: t("schedules.deleteBody") },
  );
  const toggle = useMutation({
    mutationFn: (schedule: MaintenanceSchedule) =>
      unwrap(
        api.PATCH("/api/v1/vehicles/{vehicle_id}/maintenance-schedules/{schedule_id}", {
          params: { path: { vehicle_id: vehicle.id, schedule_id: schedule.id } },
          body: { enabled: !schedule.enabled },
        }),
      ),
    onSuccess: (schedule) =>
      toast.success(schedule.enabled ? t("schedules.resumed") : t("schedules.paused")),
    onError: (error) => toast.error(errorMessage(error, t)),
  });

  const sorted = [...(schedules.data ?? [])].sort(
    (a, b) =>
      Number(b.enabled) - Number(a.enabled) ||
      SEVERITY.indexOf(a.status) - SEVERITY.indexOf(b.status),
  );

  return (
    <>
      <Toolbar
        actions={
          canEdit && (
            <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
              {t("schedules.create")}
            </Button>
          )
        }
      >
        <p className="max-w-prose text-sm text-steel">{t("schedules.intro")}</p>
      </Toolbar>
      <Panel bodyClassName="py-1">
        {schedules.isPending ? (
          <LoadingState />
        ) : schedules.isError ? (
          <ErrorState error={schedules.error} onRetry={() => void schedules.refetch()} />
        ) : sorted.length === 0 ? (
          <EmptyState
            title={t("schedules.emptyTitle")}
            body={t("schedules.emptyBody")}
            action={
              canEdit && (
                <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
                  {t("schedules.create")}
                </Button>
              )
            }
          />
        ) : (
          <ul className="divide-y divide-rule">
            {sorted.map((schedule) => (
              <ScheduleRow
                key={schedule.id}
                schedule={schedule}
                actions={
                  canEdit && (
                    <RowMenu
                      label={t("common.moreActions")}
                      actions={[
                        {
                          label: t("schedules.recordService"),
                          onSelect: () => setRecording(schedule),
                        },
                        { label: t("common.edit"), onSelect: () => setEditing(schedule) },
                        {
                          label: schedule.enabled ? t("schedules.pause") : t("schedules.resume"),
                          onSelect: () => toggle.mutate(schedule),
                        },
                        {
                          label: t("common.delete"),
                          danger: true,
                          onSelect: () => remove.ask(schedule),
                        },
                      ]}
                    />
                  )
                }
              />
            ))}
          </ul>
        )}
      </Panel>

      {editing && (
        <ScheduleFormDialog
          vehicle={vehicle}
          schedule={editing === "new" ? undefined : editing}
          scheduledTypeIds={sorted.map((schedule) => schedule.maintenance_type.id)}
          onClose={() => setEditing(null)}
        />
      )}
      {recording && (
        <RecordFormDialog
          vehicle={vehicle}
          typeId={recording.maintenance_type.id}
          onClose={() => setRecording(null)}
        />
      )}
      {remove.dialog}
    </>
  );
}

function ScheduleRow({
  schedule,
  actions,
}: {
  schedule: MaintenanceSchedule;
  actions: React.ReactNode;
}) {
  const { t } = useTranslation();
  const format = useFormat();
  const dueText = useDueText();
  const every = [
    schedule.interval_km ? format.distance(schedule.interval_km) : null,
    schedule.interval_months ? t("schedules.months", { count: schedule.interval_months }) : null,
  ]
    .filter(Boolean)
    .join(t("due.or"));
  const at = (date: string | null, km: number | null) =>
    [date ? format.date(date) : null, km !== null ? format.distance(km) : null]
      .filter(Boolean)
      .join(t("due.or"));
  const last = [
    schedule.last_service_date ? format.date(schedule.last_service_date) : null,
    schedule.last_service_mileage !== null ? format.distance(schedule.last_service_mileage) : null,
  ]
    .filter(Boolean)
    .join(", ");
  const next = at(schedule.next_service_date, schedule.next_service_mileage);

  return (
    <ItemRow
      title={
        <span className="flex flex-wrap items-center gap-2">
          {schedule.maintenance_type.name}
          {!schedule.enabled && <Badge tone="neutral">{t("schedules.pausedBadge")}</Badge>}
        </span>
      }
      details={
        <span className="flex flex-col">
          {every && <span>{t("schedules.every", { interval: every })}</span>}
          <span>
            {last ? t("schedules.last", { value: last }) : t("schedules.neverDone")}
            {next && <> {t("schedules.next", { value: next })}</>}
          </span>
        </span>
      }
      aside={
        schedule.enabled && (
          <>
            <StatusBadge status={schedule.status} />
            {schedule.status !== "unknown" && (
              <span className="text-sm text-steel">{dueText(schedule)}</span>
            )}
          </>
        )
      }
      actions={actions}
    />
  );
}
