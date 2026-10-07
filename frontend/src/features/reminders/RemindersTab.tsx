import { useMutation } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent, unwrap } from "@/api/client";
import type { Reminder } from "@/api/types";
import {
  Button,
  EmptyState,
  errorMessage,
  ErrorState,
  FilterSelect,
  ItemRow,
  LoadingState,
  Panel,
  RowMenu,
  StatusBadge,
  Toolbar,
  useToast,
} from "@/components/ui";
import { useDueText } from "@/features/maintenance/useDueText";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { useFormat } from "@/lib/useFormat";
import { useSearchFilters } from "@/lib/useSearchFilters";

import { useReminders } from "./queries";
import { ReminderFormDialog } from "./ReminderFormDialog";

export function RemindersTab() {
  const { t } = useTranslation();
  const toast = useToast();
  const format = useFormat();
  const dueText = useDueText();
  const { vehicle, canEdit } = useVehicleContext();
  const { values, update } = useSearchFilters({ show: "open" });
  const done = values.show === "done";
  const reminders = useReminders(vehicle.id, done);
  const [editing, setEditing] = useState<Reminder | "new" | null>(null);
  const remove = useConfirmDelete(
    (reminder: Reminder) =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/reminders/{reminder_id}", {
          params: { path: { vehicle_id: vehicle.id, reminder_id: reminder.id } },
        }),
      ),
    { successMessage: t("reminders.deleted") },
  );
  const complete = useMutation({
    mutationFn: (reminder: Reminder) =>
      unwrap(
        api.PATCH("/api/v1/vehicles/{vehicle_id}/reminders/{reminder_id}", {
          params: { path: { vehicle_id: vehicle.id, reminder_id: reminder.id } },
          body: { completed: !reminder.completed_at },
        }),
      ),
    onSuccess: (reminder) =>
      toast.success(reminder.completed_at ? t("reminders.done") : t("reminders.reopened")),
    onError: (error) => toast.error(errorMessage(error, t)),
  });

  const when = (reminder: Reminder) =>
    [
      reminder.due_date ? format.date(reminder.due_date) : null,
      reminder.due_mileage !== null ? format.distance(reminder.due_mileage) : null,
    ]
      .filter(Boolean)
      .join(t("due.or"));

  return (
    <>
      <Toolbar
        actions={
          canEdit && (
            <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
              {t("reminders.add")}
            </Button>
          )
        }
      >
        <FilterSelect
          label={t("reminders.show")}
          value={values.show}
          onChange={(event) => update({ show: event.target.value })}
        >
          <option value="open">{t("reminders.open")}</option>
          <option value="done">{t("reminders.completed")}</option>
        </FilterSelect>
      </Toolbar>
      <Panel bodyClassName="py-1">
        {reminders.isPending ? (
          <LoadingState />
        ) : reminders.isError ? (
          <ErrorState error={reminders.error} onRetry={() => void reminders.refetch()} />
        ) : reminders.data.length === 0 ? (
          <EmptyState
            title={done ? t("reminders.noneDone") : t("reminders.emptyTitle")}
            body={done ? undefined : t("reminders.emptyBody")}
          />
        ) : (
          <ul className="divide-y divide-rule">
            {reminders.data.map((reminder) => (
              <ItemRow
                key={reminder.id}
                title={reminder.title}
                details={
                  <span className="flex flex-col">
                    <span>
                      {reminder.completed_at
                        ? t("reminders.doneOn", { date: format.date(reminder.completed_at) })
                        : t("reminders.dueOn", { when: when(reminder) })}
                    </span>
                    {reminder.notes && <span>{reminder.notes}</span>}
                  </span>
                }
                aside={
                  !reminder.completed_at && (
                    <>
                      <StatusBadge status={reminder.status ?? "unknown"} />
                      <span className="text-sm text-steel">
                        {dueText({ ...reminder, status: reminder.status ?? "unknown" })}
                      </span>
                    </>
                  )
                }
                actions={
                  canEdit && (
                    <RowMenu
                      label={t("common.moreActions")}
                      actions={[
                        {
                          label: reminder.completed_at
                            ? t("reminders.reopen")
                            : t("reminders.markDone"),
                          onSelect: () => complete.mutate(reminder),
                        },
                        { label: t("common.edit"), onSelect: () => setEditing(reminder) },
                        {
                          label: t("common.delete"),
                          danger: true,
                          onSelect: () => remove.ask(reminder),
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
        <ReminderFormDialog
          vehicle={vehicle}
          reminder={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {remove.dialog}
    </>
  );
}
