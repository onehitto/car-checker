import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import type { Reminder, Vehicle } from "@/api/types";
import { Field, FieldRow, FormDialog, Input, Textarea } from "@/components/ui";
import { i18n } from "@/i18n";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useFormat } from "@/lib/useFormat";
import { asInput, field } from "@/lib/validation";

const schema = z
  .object({
    title: field.text(200),
    due_date: field.optionalDate(),
    due_mileage: field.optionalInt(0, 2_000_000),
    warning_before_days: field.int(0, 365),
    warning_before_km: field.int(0, 100_000),
    notes: field.optionalText(10_000),
  })
  .refine((values) => values.due_date !== null || values.due_mileage !== null, {
    path: ["due_date"],
    error: () => i18n.t("reminders.fields.whenRequired"),
  });

/** Anything else to remember: renew a badge, check the spare, change the wipers... */
export function ReminderFormDialog({
  vehicle,
  reminder,
  onClose,
}: {
  vehicle: Vehicle;
  reminder?: Reminder;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const format = useFormat();
  const form = useZodForm(schema, {
    title: reminder?.title ?? "",
    due_date: asInput(reminder?.due_date),
    due_mileage: reminder?.due_mileage != null ? String(format.toUnit(reminder.due_mileage)) : "",
    warning_before_days: String(reminder?.warning_before_days ?? 7),
    warning_before_km: String(format.toUnit(reminder?.warning_before_km ?? 500)),
    notes: asInput(reminder?.notes),
  });
  const errors = form.formState.errors;

  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (values) => {
      const body = {
        ...values,
        due_mileage: values.due_mileage === null ? null : format.toKm(values.due_mileage),
        warning_before_km: format.toKm(values.warning_before_km),
      };
      const path = { vehicle_id: vehicle.id };
      return reminder
        ? unwrap(
            api.PATCH("/api/v1/vehicles/{vehicle_id}/reminders/{reminder_id}", {
              params: { path: { ...path, reminder_id: reminder.id } },
              body,
            }),
          )
        : unwrap(api.POST("/api/v1/vehicles/{vehicle_id}/reminders", { params: { path }, body }));
    },
    {
      successMessage: reminder ? t("reminders.updated") : t("reminders.added"),
      onSuccess: onClose,
    },
  );

  const unit = format.unit;
  return (
    <FormDialog
      title={reminder ? t("reminders.editTitle") : t("reminders.addTitle")}
      description={t("reminders.formBody")}
      submitLabel={reminder ? t("common.saveChanges") : t("reminders.add")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <Field label={t("reminders.fields.title")} error={errors.title?.message}>
        {(props) => (
          <Input
            placeholder={t("reminders.fields.titlePlaceholder")}
            {...props}
            {...form.register("title")}
          />
        )}
      </Field>
      <FieldRow>
        <Field label={t("reminders.fields.dueDate")} optional error={errors.due_date?.message}>
          {(props) => <Input type="date" {...props} {...form.register("due_date")} />}
        </Field>
        <Field
          label={t("reminders.fields.dueMileage", { unit })}
          optional
          error={errors.due_mileage?.message}
        >
          {(props) => <Input inputMode="numeric" {...props} {...form.register("due_mileage")} />}
        </Field>
      </FieldRow>
      <FieldRow>
        <Field label={t("schedules.fields.warnDays")} error={errors.warning_before_days?.message}>
          {(props) => (
            <Input inputMode="numeric" {...props} {...form.register("warning_before_days")} />
          )}
        </Field>
        <Field
          label={t("schedules.fields.warnKm", { unit })}
          error={errors.warning_before_km?.message}
        >
          {(props) => (
            <Input inputMode="numeric" {...props} {...form.register("warning_before_km")} />
          )}
        </Field>
      </FieldRow>
      <Field label={t("common.notes")} optional error={errors.notes?.message}>
        {(props) => <Textarea rows={2} {...props} {...form.register("notes")} />}
      </Field>
    </FormDialog>
  );
}
