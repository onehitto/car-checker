import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { OIL_TYPES } from "@/api/enums";
import type { OilChange, Vehicle } from "@/api/types";
import { Checkbox, Field, FieldRow, FormDialog, Input, Select, Textarea } from "@/components/ui";
import { GarageSelect } from "@/features/catalog/selects";
import { i18n } from "@/i18n";
import { todayIso } from "@/lib/format";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useFormat } from "@/lib/useFormat";
import { asInput, field } from "@/lib/validation";

const VISCOSITY = /^(\d{1,2}W-?\d{2}|SAE ?\d{2})$/i;

const schema = z.object({
  service_date: field.date(),
  mileage: field.optionalInt(0, 2_000_000),
  oil_brand: field.optionalText(80),
  oil_type: field.optionalChoice(OIL_TYPES),
  oil_viscosity: field.optionalText(20).pipe(
    z
      .string()
      .regex(VISCOSITY, { error: () => i18n.t("oil.fields.viscosityInvalid") })
      .transform((value) => value.toUpperCase())
      .nullable(),
  ),
  oil_quantity_liters: field.optionalDecimal(2, 2),
  oil_filter_changed: z.boolean(),
  filter_brand: field.optionalText(80),
  filter_reference: field.optionalText(80),
  cost: field.optionalDecimal(),
  labor_cost: field.optionalDecimal(),
  parts_cost: field.optionalDecimal(),
  garage_id: field.optionalId(),
  notes: field.optionalText(10_000),
});

export function OilChangeFormDialog({
  vehicle,
  oilChange,
  onClose,
}: {
  vehicle: Vehicle;
  oilChange?: OilChange;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const format = useFormat();
  const form = useZodForm(schema, {
    service_date: oilChange?.service_date ?? todayIso(),
    mileage:
      oilChange?.mileage != null
        ? String(format.toUnit(oilChange.mileage))
        : oilChange
          ? ""
          : String(format.toUnit(vehicle.current_mileage)),
    oil_brand: asInput(oilChange?.oil_brand),
    oil_type: oilChange?.oil_type ?? "",
    oil_viscosity: asInput(oilChange?.oil_viscosity),
    oil_quantity_liters: asInput(oilChange?.oil_quantity_liters),
    oil_filter_changed: oilChange?.oil_filter_changed ?? true,
    filter_brand: asInput(oilChange?.filter_brand),
    filter_reference: asInput(oilChange?.filter_reference),
    cost: asInput(oilChange?.cost),
    labor_cost: asInput(oilChange?.labor_cost),
    parts_cost: asInput(oilChange?.parts_cost),
    garage_id: oilChange?.garage?.id ?? "",
    notes: asInput(oilChange?.notes),
  });
  const errors = form.formState.errors;
  const currency = vehicle.currency;

  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (values) => {
      const body = {
        ...values,
        mileage: values.mileage === null ? null : format.toKm(values.mileage),
      };
      const path = { vehicle_id: vehicle.id };
      return oilChange
        ? unwrap(
            api.PATCH("/api/v1/vehicles/{vehicle_id}/oil-changes/{record_id}", {
              params: { path: { ...path, record_id: oilChange.id } },
              body,
            }),
          )
        : unwrap(api.POST("/api/v1/vehicles/{vehicle_id}/oil-changes", { params: { path }, body }));
    },
    {
      successMessage: oilChange ? t("maintenance.updated") : t("oil.recorded"),
      onSuccess: onClose,
    },
  );

  return (
    <FormDialog
      size="lg"
      title={oilChange ? t("oil.editTitle") : t("oil.recordTitle")}
      description={t("oil.formBody")}
      submitLabel={oilChange ? t("common.saveChanges") : t("oil.record")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
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
      <FieldRow>
        <Field label={t("oil.fields.brand")} optional error={errors.oil_brand?.message}>
          {(props) => (
            <Input placeholder="Total Quartz" {...props} {...form.register("oil_brand")} />
          )}
        </Field>
        <Field label={t("oil.fields.type")} optional error={errors.oil_type?.message}>
          {(props) => (
            <Select {...props} {...form.register("oil_type")}>
              <option value="">{t("common.notSet")}</option>
              {OIL_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`enums.oilType.${type}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </FieldRow>
      <FieldRow>
        <Field
          label={t("oil.fields.viscosity")}
          optional
          hint={t("oil.fields.viscosityHint")}
          error={errors.oil_viscosity?.message}
        >
          {(props) => (
            <Input dir="ltr" placeholder="5W-30" {...props} {...form.register("oil_viscosity")} />
          )}
        </Field>
        <Field
          label={t("oil.fields.quantity")}
          optional
          error={errors.oil_quantity_liters?.message}
        >
          {(props) => (
            <Input inputMode="decimal" {...props} {...form.register("oil_quantity_liters")} />
          )}
        </Field>
      </FieldRow>
      <Checkbox label={t("oil.fields.filterChanged")} {...form.register("oil_filter_changed")} />
      <FieldRow>
        <Field label={t("oil.fields.filterBrand")} optional error={errors.filter_brand?.message}>
          {(props) => <Input {...props} {...form.register("filter_brand")} />}
        </Field>
        <Field
          label={t("oil.fields.filterReference")}
          optional
          error={errors.filter_reference?.message}
        >
          {(props) => <Input dir="ltr" {...props} {...form.register("filter_reference")} />}
        </Field>
      </FieldRow>
      <FieldRow columns={3}>
        <Field label={t("common.totalIn", { currency })} optional error={errors.cost?.message}>
          {(props) => <Input inputMode="decimal" {...props} {...form.register("cost")} />}
        </Field>
        <Field label={t("maintenance.fields.labor")} optional error={errors.labor_cost?.message}>
          {(props) => <Input inputMode="decimal" {...props} {...form.register("labor_cost")} />}
        </Field>
        <Field label={t("maintenance.fields.parts")} optional error={errors.parts_cost?.message}>
          {(props) => <Input inputMode="decimal" {...props} {...form.register("parts_cost")} />}
        </Field>
      </FieldRow>
      <Field label={t("common.notes")} optional error={errors.notes?.message}>
        {(props) => <Textarea rows={2} {...props} {...form.register("notes")} />}
      </Field>
    </FormDialog>
  );
}
