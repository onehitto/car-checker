import { useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import type { MaintenanceSchedule, Vehicle } from "@/api/types";
import { Checkbox, Field, FieldRow, FormDialog, Input, Textarea } from "@/components/ui";
import { useMaintenanceTypes } from "@/features/catalog/queries";
import { MaintenanceTypeSelect } from "@/features/catalog/selects";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useFormat } from "@/lib/useFormat";
import { asInput, field } from "@/lib/validation";

const schema = z.object({
  maintenance_type_id: field.id(),
  interval_km: field.optionalPositiveInt(1_000_000),
  interval_months: field.optionalPositiveInt(240),
  last_service_date: field.optionalDate(),
  last_service_mileage: field.optionalInt(0, 2_000_000),
  next_service_date: field.optionalDate(),
  next_service_mileage: field.optionalInt(0, 2_000_000),
  warning_before_km: field.int(0, 100_000),
  warning_before_days: field.int(0, 365),
  enabled: z.boolean(),
  notes: field.optionalText(10_000),
});

interface ScheduleFormDialogProps {
  vehicle: Vehicle;
  schedule?: MaintenanceSchedule;
  /** Types that already have a schedule (one schedule per type). */
  scheduledTypeIds: string[];
  onClose: () => void;
}

export function ScheduleFormDialog({
  vehicle,
  schedule,
  scheduledTypeIds,
  onClose,
}: ScheduleFormDialogProps) {
  const { t } = useTranslation();
  const format = useFormat();
  const types = useMaintenanceTypes();
  const km = (value: number | null | undefined) =>
    value == null ? "" : String(format.toUnit(value));
  const form = useZodForm(schema, {
    maintenance_type_id: schedule?.maintenance_type.id ?? "",
    interval_km: km(schedule?.interval_km),
    interval_months: asInput(schedule?.interval_months),
    last_service_date: asInput(schedule?.last_service_date),
    last_service_mileage: km(schedule?.last_service_mileage),
    next_service_date: asInput(schedule?.next_service_date),
    next_service_mileage: km(schedule?.next_service_mileage),
    warning_before_km: String(format.toUnit(schedule?.warning_before_km ?? 1000)),
    warning_before_days: String(schedule?.warning_before_days ?? 30),
    enabled: schedule?.enabled ?? true,
    notes: asInput(schedule?.notes),
  });
  const errors = form.formState.errors;
  const typeId = useWatch({ control: form.control, name: "maintenance_type_id" });
  const type = types.data?.find((item) => item.id === typeId);

  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    ({ maintenance_type_id, ...values }) => {
      const toKm = (value: number | null) => (value === null ? null : format.toKm(value));
      const body = {
        ...values,
        interval_km: toKm(values.interval_km),
        last_service_mileage: toKm(values.last_service_mileage),
        next_service_mileage: toKm(values.next_service_mileage),
        warning_before_km: format.toKm(values.warning_before_km),
      };
      const path = { vehicle_id: vehicle.id };
      return schedule
        ? unwrap(
            api.PATCH("/api/v1/vehicles/{vehicle_id}/maintenance-schedules/{schedule_id}", {
              params: { path: { ...path, schedule_id: schedule.id } },
              body,
            }),
          )
        : unwrap(
            api.POST("/api/v1/vehicles/{vehicle_id}/maintenance-schedules", {
              params: { path },
              body: { ...body, maintenance_type_id },
            }),
          );
    },
    {
      successMessage: schedule ? t("schedules.updated") : t("schedules.created"),
      onSuccess: onClose,
    },
  );

  const unit = format.unit;
  return (
    <FormDialog
      size="lg"
      title={
        schedule
          ? t("schedules.editTitle", { name: schedule.maintenance_type.name })
          : t("schedules.createTitle")
      }
      description={t("schedules.formBody")}
      submitLabel={schedule ? t("common.saveChanges") : t("schedules.create")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      {!schedule && (
        <Field label={t("maintenance.fields.type")} error={errors.maintenance_type_id?.message}>
          {(props) => (
            <MaintenanceTypeSelect
              exclude={scheduledTypeIds}
              {...props}
              {...form.register("maintenance_type_id")}
            />
          )}
        </Field>
      )}
      <FieldRow>
        <Field
          label={t("schedules.fields.everyDistance", { unit })}
          optional
          hint={
            type?.default_interval_km
              ? t("schedules.fields.usual", { value: format.distance(type.default_interval_km) })
              : undefined
          }
          error={errors.interval_km?.message}
        >
          {(props) => <Input inputMode="numeric" {...props} {...form.register("interval_km")} />}
        </Field>
        <Field
          label={t("schedules.fields.everyMonths")}
          optional
          hint={
            type?.default_interval_months
              ? t("schedules.fields.usual", {
                  value: t("schedules.months", { count: type.default_interval_months }),
                })
              : undefined
          }
          error={errors.interval_months?.message}
        >
          {(props) => (
            <Input inputMode="numeric" {...props} {...form.register("interval_months")} />
          )}
        </Field>
      </FieldRow>
      <FieldRow>
        <Field
          label={t("schedules.fields.lastDate")}
          optional
          hint={t("schedules.fields.lastHint")}
          error={errors.last_service_date?.message}
        >
          {(props) => <Input type="date" {...props} {...form.register("last_service_date")} />}
        </Field>
        <Field
          label={t("schedules.fields.lastMileage", { unit })}
          optional
          error={errors.last_service_mileage?.message}
        >
          {(props) => (
            <Input inputMode="numeric" {...props} {...form.register("last_service_mileage")} />
          )}
        </Field>
      </FieldRow>
      <FieldRow>
        <Field
          label={t("schedules.fields.nextDate")}
          optional
          hint={t("schedules.fields.nextHint")}
          error={errors.next_service_date?.message}
        >
          {(props) => <Input type="date" {...props} {...form.register("next_service_date")} />}
        </Field>
        <Field
          label={t("schedules.fields.nextMileage", { unit })}
          optional
          error={errors.next_service_mileage?.message}
        >
          {(props) => (
            <Input inputMode="numeric" {...props} {...form.register("next_service_mileage")} />
          )}
        </Field>
      </FieldRow>
      <FieldRow>
        <Field
          label={t("schedules.fields.warnKm", { unit })}
          error={errors.warning_before_km?.message}
        >
          {(props) => (
            <Input inputMode="numeric" {...props} {...form.register("warning_before_km")} />
          )}
        </Field>
        <Field label={t("schedules.fields.warnDays")} error={errors.warning_before_days?.message}>
          {(props) => (
            <Input inputMode="numeric" {...props} {...form.register("warning_before_days")} />
          )}
        </Field>
      </FieldRow>
      {schedule && <Checkbox label={t("schedules.fields.enabled")} {...form.register("enabled")} />}
      <Field label={t("common.notes")} optional error={errors.notes?.message}>
        {(props) => <Textarea rows={2} {...props} {...form.register("notes")} />}
      </Field>
    </FormDialog>
  );
}
