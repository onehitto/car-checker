import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import type { Part, Vehicle } from "@/api/types";
import { Field, FieldRow, FormDialog, Input, Textarea } from "@/components/ui";
import { GarageSelect, PartTypeSelect } from "@/features/catalog/selects";
import { todayIso } from "@/lib/format";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useFormat } from "@/lib/useFormat";
import { asInput, field } from "@/lib/validation";

const schema = z.object({
  part_type_id: field.id(),
  part_name: field.optionalText(150),
  brand: field.optionalText(80),
  reference_number: field.optionalText(80),
  serial_number: field.optionalText(80),
  position: field.optionalText(30),
  quantity: field.int(1, 100),
  installed_date: field.date(),
  installed_mileage: field.optionalInt(0, 2_000_000),
  price: field.optionalDecimal(),
  labor_cost: field.optionalDecimal(),
  garage_id: field.optionalId(),
  warranty_expiration_date: field.optionalDate(),
  expected_lifetime_km: field.optionalPositiveInt(1_000_000),
  expected_lifetime_months: field.optionalPositiveInt(240),
  notes: field.optionalText(10_000),
});

/** A part fitted to the vehicle: what, when, how much, and how long it should last. */
export function PartFormDialog({
  vehicle,
  part,
  onClose,
}: {
  vehicle: Vehicle;
  part?: Part;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const format = useFormat();
  const km = (value: number | null | undefined) =>
    value == null ? "" : String(format.toUnit(value));
  const form = useZodForm(schema, {
    part_type_id: part?.part_type.id ?? "",
    part_name: asInput(part?.part_name),
    brand: asInput(part?.brand),
    reference_number: asInput(part?.reference_number),
    serial_number: asInput(part?.serial_number),
    position: asInput(part?.position),
    quantity: String(part?.quantity ?? 1),
    installed_date: part?.installed_date ?? todayIso(),
    installed_mileage: part ? km(part.installed_mileage) : km(vehicle.current_mileage),
    price: asInput(part?.price),
    labor_cost: asInput(part?.labor_cost),
    garage_id: part?.garage?.id ?? "",
    warranty_expiration_date: asInput(part?.warranty_expiration_date),
    expected_lifetime_km: km(part?.expected_lifetime_km),
    expected_lifetime_months: asInput(part?.expected_lifetime_months),
    notes: asInput(part?.notes),
  });
  const errors = form.formState.errors;
  const currency = vehicle.currency;

  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (values) => {
      const toKm = (value: number | null) => (value === null ? null : format.toKm(value));
      const body = {
        ...values,
        // An empty name falls back to the type name (the name itself cannot be cleared).
        part_name: values.part_name ?? undefined,
        installed_mileage: toKm(values.installed_mileage),
        expected_lifetime_km: toKm(values.expected_lifetime_km),
      };
      const path = { vehicle_id: vehicle.id };
      return part
        ? unwrap(
            api.PATCH("/api/v1/vehicles/{vehicle_id}/parts/{part_id}", {
              params: { path: { ...path, part_id: part.id } },
              body,
            }),
          )
        : unwrap(api.POST("/api/v1/vehicles/{vehicle_id}/parts", { params: { path }, body }));
    },
    { successMessage: part ? t("parts.updated") : t("parts.added"), onSuccess: onClose },
  );

  const unit = format.unitLabel;
  return (
    <FormDialog
      size="lg"
      title={part ? t("parts.editTitle") : t("parts.addTitle")}
      description={t("parts.formBody")}
      submitLabel={part ? t("common.saveChanges") : t("parts.add")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <FieldRow>
        <Field label={t("maintenance.fields.type")} error={errors.part_type_id?.message}>
          {(props) => <PartTypeSelect {...props} {...form.register("part_type_id")} />}
        </Field>
        <Field
          label={t("parts.fields.name")}
          optional
          hint={t("parts.fields.nameHint")}
          error={errors.part_name?.message}
        >
          {(props) => <Input {...props} {...form.register("part_name")} />}
        </Field>
      </FieldRow>
      <FieldRow columns={3}>
        <Field label={t("parts.fields.brand")} optional error={errors.brand?.message}>
          {(props) => <Input {...props} {...form.register("brand")} />}
        </Field>
        <Field
          label={t("parts.fields.reference")}
          optional
          error={errors.reference_number?.message}
        >
          {(props) => <Input dir="ltr" {...props} {...form.register("reference_number")} />}
        </Field>
        <Field label={t("parts.fields.serial")} optional error={errors.serial_number?.message}>
          {(props) => <Input dir="ltr" {...props} {...form.register("serial_number")} />}
        </Field>
      </FieldRow>
      <FieldRow columns={3}>
        <Field
          label={t("parts.fields.position")}
          optional
          hint={t("parts.fields.positionHint")}
          error={errors.position?.message}
        >
          {(props) => <Input {...props} {...form.register("position")} />}
        </Field>
        <Field label={t("parts.fields.quantity")} error={errors.quantity?.message}>
          {(props) => <Input inputMode="numeric" {...props} {...form.register("quantity")} />}
        </Field>
        <Field label={t("maintenance.fields.garage")} optional error={errors.garage_id?.message}>
          {(props) => <GarageSelect {...props} {...form.register("garage_id")} />}
        </Field>
      </FieldRow>
      <FieldRow columns={3}>
        <Field label={t("parts.fields.installedOn")} error={errors.installed_date?.message}>
          {(props) => <Input type="date" {...props} {...form.register("installed_date")} />}
        </Field>
        <Field
          label={t("parts.fields.installedAt", { unit })}
          optional
          error={errors.installed_mileage?.message}
        >
          {(props) => (
            <Input inputMode="numeric" {...props} {...form.register("installed_mileage")} />
          )}
        </Field>
        <Field
          label={t("parts.fields.warranty")}
          optional
          error={errors.warranty_expiration_date?.message}
        >
          {(props) => (
            <Input type="date" {...props} {...form.register("warranty_expiration_date")} />
          )}
        </Field>
      </FieldRow>
      <FieldRow>
        <Field label={t("parts.fields.price", { currency })} optional error={errors.price?.message}>
          {(props) => <Input inputMode="decimal" {...props} {...form.register("price")} />}
        </Field>
        <Field label={t("maintenance.fields.labor")} optional error={errors.labor_cost?.message}>
          {(props) => <Input inputMode="decimal" {...props} {...form.register("labor_cost")} />}
        </Field>
      </FieldRow>
      <FieldRow>
        <Field
          label={t("parts.fields.lifetimeKm", { unit })}
          optional
          hint={t("parts.fields.lifetimeHint")}
          error={errors.expected_lifetime_km?.message}
        >
          {(props) => (
            <Input inputMode="numeric" {...props} {...form.register("expected_lifetime_km")} />
          )}
        </Field>
        <Field
          label={t("parts.fields.lifetimeMonths")}
          optional
          error={errors.expected_lifetime_months?.message}
        >
          {(props) => (
            <Input inputMode="numeric" {...props} {...form.register("expected_lifetime_months")} />
          )}
        </Field>
      </FieldRow>
      <Field label={t("common.notes")} optional error={errors.notes?.message}>
        {(props) => <Textarea rows={2} {...props} {...form.register("notes")} />}
      </Field>
    </FormDialog>
  );
}
