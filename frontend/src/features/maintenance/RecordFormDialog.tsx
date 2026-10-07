import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { MAINTENANCE_KINDS } from "@/api/enums";
import type { MaintenanceRecord, Vehicle } from "@/api/types";
import { Field, FieldRow, FormDialog, Input, Select, Textarea } from "@/components/ui";
import { GarageSelect, MaintenanceTypeSelect } from "@/features/catalog/selects";
import { todayIso } from "@/lib/format";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useFormat } from "@/lib/useFormat";
import { asInput, field } from "@/lib/validation";

const schema = z.object({
  maintenance_type_id: field.id(),
  kind: field.choice(MAINTENANCE_KINDS),
  title: field.optionalText(200),
  service_date: field.date(),
  mileage: field.optionalInt(0, 2_000_000),
  cost: field.optionalDecimal(),
  labor_cost: field.optionalDecimal(),
  parts_cost: field.optionalDecimal(),
  garage_id: field.optionalId(),
  description: field.optionalText(10_000),
  notes: field.optionalText(10_000),
});

interface RecordFormDialogProps {
  vehicle: Vehicle;
  record?: MaintenanceRecord;
  /** Pre-selected type ("Record this service" from a schedule). */
  typeId?: string;
  onClose: () => void;
}

/** Record a service or a repair, or edit one. */
export function RecordFormDialog({ vehicle, record, typeId, onClose }: RecordFormDialogProps) {
  const { t } = useTranslation();
  const format = useFormat();
  const form = useZodForm(schema, {
    maintenance_type_id: record?.maintenance_type.id ?? typeId ?? "",
    kind: record?.kind ?? "maintenance",
    title: asInput(record?.title),
    service_date: record?.service_date ?? todayIso(),
    mileage:
      record?.mileage != null
        ? String(format.toUnit(record.mileage))
        : record
          ? ""
          : String(format.toUnit(vehicle.current_mileage)),
    cost: asInput(record?.cost),
    labor_cost: asInput(record?.labor_cost),
    parts_cost: asInput(record?.parts_cost),
    garage_id: record?.garage?.id ?? "",
    description: asInput(record?.description),
    notes: asInput(record?.notes),
  });
  const errors = form.formState.errors;
  const currency = vehicle.currency;

  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (values) => {
      const body = {
        ...values,
        // An empty title falls back to the type name (the title itself cannot be cleared).
        title: values.title ?? undefined,
        mileage: values.mileage === null ? null : format.toKm(values.mileage),
      };
      const path = { vehicle_id: vehicle.id };
      return record
        ? unwrap(
            api.PATCH("/api/v1/vehicles/{vehicle_id}/maintenance/{record_id}", {
              params: { path: { ...path, record_id: record.id } },
              body,
            }),
          )
        : unwrap(api.POST("/api/v1/vehicles/{vehicle_id}/maintenance", { params: { path }, body }));
    },
    {
      successMessage: record ? t("maintenance.updated") : t("maintenance.recorded"),
      onSuccess: onClose,
    },
  );

  return (
    <FormDialog
      size="lg"
      title={record ? t("maintenance.editTitle") : t("maintenance.recordTitle")}
      submitLabel={record ? t("common.saveChanges") : t("maintenance.record")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <FieldRow>
        <Field label={t("maintenance.fields.type")} error={errors.maintenance_type_id?.message}>
          {(props) => (
            <MaintenanceTypeSelect {...props} {...form.register("maintenance_type_id")} />
          )}
        </Field>
        <Field label={t("maintenance.fields.kind")} error={errors.kind?.message}>
          {(props) => (
            <Select {...props} {...form.register("kind")}>
              {MAINTENANCE_KINDS.map((kind) => (
                <option key={kind} value={kind}>
                  {t(`enums.maintenanceKind.${kind}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </FieldRow>
      <Field
        label={t("maintenance.fields.title")}
        optional
        hint={t("maintenance.fields.titleHint")}
        error={errors.title?.message}
      >
        {(props) => <Input {...props} {...form.register("title")} />}
      </Field>
      <FieldRow columns={3}>
        <Field label={t("common.date")} error={errors.service_date?.message}>
          {(props) => <Input type="date" {...props} {...form.register("service_date")} />}
        </Field>
        <Field
          label={t("common.mileageIn", { unit: format.unit })}
          optional
          error={errors.mileage?.message}
        >
          {(props) => <Input inputMode="numeric" {...props} {...form.register("mileage")} />}
        </Field>
        <Field label={t("maintenance.fields.garage")} optional error={errors.garage_id?.message}>
          {(props) => <GarageSelect {...props} {...form.register("garage_id")} />}
        </Field>
      </FieldRow>
      <FieldRow columns={3}>
        <Field
          label={t("common.totalIn", { currency })}
          optional
          hint={t("maintenance.fields.costHint")}
          error={errors.cost?.message}
        >
          {(props) => <Input inputMode="decimal" {...props} {...form.register("cost")} />}
        </Field>
        <Field label={t("maintenance.fields.labor")} optional error={errors.labor_cost?.message}>
          {(props) => <Input inputMode="decimal" {...props} {...form.register("labor_cost")} />}
        </Field>
        <Field label={t("maintenance.fields.parts")} optional error={errors.parts_cost?.message}>
          {(props) => <Input inputMode="decimal" {...props} {...form.register("parts_cost")} />}
        </Field>
      </FieldRow>
      <Field label={t("maintenance.fields.workDone")} optional error={errors.description?.message}>
        {(props) => <Textarea rows={2} {...props} {...form.register("description")} />}
      </Field>
      <Field label={t("common.notes")} optional error={errors.notes?.message}>
        {(props) => <Textarea rows={2} {...props} {...form.register("notes")} />}
      </Field>
    </FormDialog>
  );
}
