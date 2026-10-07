import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { PUMP_FUELS } from "@/api/enums";
import type { FuelRecord, Vehicle } from "@/api/types";
import { Checkbox, Field, FieldRow, FormDialog, Input, Select, Textarea } from "@/components/ui";
import { todayIso } from "@/lib/format";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useFormat } from "@/lib/useFormat";
import { asInput, field } from "@/lib/validation";

const schema = z.object({
  fill_date: field.date(),
  mileage: field.int(0, 2_000_000),
  liters: field.decimal(3, 4),
  price_per_liter: field.optionalDecimal(4, 6),
  total_price: field.optionalDecimal(),
  full_tank: z.boolean(),
  missed_previous: z.boolean(),
  fuel_type: field.optionalChoice(PUMP_FUELS),
  gas_station: field.optionalText(120),
  notes: field.optionalText(10_000),
});

/** Pump fuel matching the vehicle's fuel (hybrids run on petrol). */
function defaultPumpFuel(vehicle: Vehicle): (typeof PUMP_FUELS)[number] | "" {
  const fuel = vehicle.fuel_type;
  if (fuel === "hybrid" || fuel === "plug_in_hybrid") return "petrol";
  return (PUMP_FUELS as readonly string[]).includes(fuel) && fuel !== "other"
    ? (fuel as (typeof PUMP_FUELS)[number])
    : "";
}

export function FuelFormDialog({
  vehicle,
  record,
  onClose,
}: {
  vehicle: Vehicle;
  record?: FuelRecord;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const format = useFormat();
  const form = useZodForm(schema, {
    fill_date: record?.fill_date ?? todayIso(),
    mileage: record ? String(format.toUnit(record.mileage)) : "",
    liters: asInput(record?.liters),
    price_per_liter: asInput(record?.price_per_liter),
    total_price: asInput(record?.total_price),
    full_tank: record?.full_tank ?? true,
    missed_previous: record?.missed_previous ?? false,
    fuel_type: record ? (record.fuel_type ?? "") : defaultPumpFuel(vehicle),
    gas_station: asInput(record?.gas_station),
    notes: asInput(record?.notes),
  });
  const errors = form.formState.errors;
  const dirty = form.formState.dirtyFields;

  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (values) => {
      const body = { ...values, mileage: format.toKm(values.mileage) };
      // The API completes the price from the other two values: send only what the user changed
      // so an edited quantity or price does not contradict the stored total.
      if (dirty.price_per_liter && !dirty.total_price) body.total_price = null;
      else if (dirty.total_price && !dirty.price_per_liter) body.price_per_liter = null;
      else if (dirty.liters && !dirty.price_per_liter && !dirty.total_price)
        body.price_per_liter = null;
      const path = { vehicle_id: vehicle.id };
      return record
        ? unwrap(
            api.PATCH("/api/v1/vehicles/{vehicle_id}/fuel/{record_id}", {
              params: { path: { ...path, record_id: record.id } },
              body,
            }),
          )
        : unwrap(api.POST("/api/v1/vehicles/{vehicle_id}/fuel", { params: { path }, body }));
    },
    { successMessage: record ? t("fuel.updated") : t("fuel.recorded"), onSuccess: onClose },
  );

  return (
    <FormDialog
      size="lg"
      title={record ? t("fuel.editTitle") : t("fuel.recordTitle")}
      description={t("fuel.formBody")}
      submitLabel={record ? t("common.saveChanges") : t("fuel.record")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <FieldRow columns={3}>
        <Field label={t("common.date")} error={errors.fill_date?.message}>
          {(props) => <Input type="date" {...props} {...form.register("fill_date")} />}
        </Field>
        <Field label={t("common.mileageIn", { unit: format.unit })} error={errors.mileage?.message}>
          {(props) => <Input inputMode="numeric" {...props} {...form.register("mileage")} />}
        </Field>
        <Field label={t("fuel.fields.liters")} error={errors.liters?.message}>
          {(props) => <Input inputMode="decimal" {...props} {...form.register("liters")} />}
        </Field>
      </FieldRow>
      <FieldRow>
        <Field
          label={t("fuel.fields.pricePerLiter", { currency: vehicle.currency })}
          optional
          hint={t("fuel.fields.priceHint")}
          error={errors.price_per_liter?.message}
        >
          {(props) => (
            <Input inputMode="decimal" {...props} {...form.register("price_per_liter")} />
          )}
        </Field>
        <Field
          label={t("common.totalIn", { currency: vehicle.currency })}
          optional
          error={errors.total_price?.message}
        >
          {(props) => <Input inputMode="decimal" {...props} {...form.register("total_price")} />}
        </Field>
      </FieldRow>
      <div className="flex flex-col gap-2">
        <Checkbox label={t("fuel.fields.fullTank")} {...form.register("full_tank")} />
        <Checkbox label={t("fuel.fields.missedPrevious")} {...form.register("missed_previous")} />
        <p className="text-sm text-steel">{t("fuel.fields.consumptionHint")}</p>
      </div>
      <FieldRow>
        <Field label={t("fuel.fields.fuel")} optional error={errors.fuel_type?.message}>
          {(props) => (
            <Select {...props} {...form.register("fuel_type")}>
              <option value="">{t("common.notSet")}</option>
              {PUMP_FUELS.map((fuel) => (
                <option key={fuel} value={fuel}>
                  {t(`enums.pumpFuel.${fuel}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("fuel.fields.station")} optional error={errors.gas_station?.message}>
          {(props) => <Input {...props} {...form.register("gas_station")} />}
        </Field>
      </FieldRow>
      <Field label={t("common.notes")} optional error={errors.notes?.message}>
        {(props) => <Textarea rows={2} {...props} {...form.register("notes")} />}
      </Field>
    </FormDialog>
  );
}
