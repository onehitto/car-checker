import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { TIRE_CONDITIONS, TIRE_POSITIONS, TIRE_SEASONS } from "@/api/enums";
import type { Tire, Vehicle } from "@/api/types";
import { Field, FieldRow, FormDialog, Input, Select, Textarea } from "@/components/ui";
import { todayIso } from "@/lib/format";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useFormat } from "@/lib/useFormat";
import { asInput, field } from "@/lib/validation";

const schema = z.object({
  brand: field.text(80),
  model: field.optionalText(80),
  size: z.string().trim().min(3).max(32),
  season: field.choice(TIRE_SEASONS),
  dot_code: field.optionalText(20),
  condition: field.optionalChoice(TIRE_CONDITIONS),
  purchase_date: field.optionalDate(),
  price: field.optionalDecimal(),
  tread_depth_mm: field.optionalDecimal(1, 2),
  pressure_notes: field.optionalText(200),
  notes: field.optionalText(10_000),
  position: field.optionalChoice(TIRE_POSITIONS),
  installed_date: field.optionalDate(),
  installed_mileage: field.optionalInt(0, 2_000_000),
});

/** Add a tire (mounted at a position or kept in storage) or edit its description. */
export function TireFormDialog({
  vehicle,
  tire,
  freePositions,
  onClose,
}: {
  vehicle: Vehicle;
  tire?: Tire;
  /** Positions without a mounted tire (for a new tire). */
  freePositions: string[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const format = useFormat();
  const form = useZodForm(schema, {
    brand: tire?.brand ?? "",
    model: asInput(tire?.model),
    size: tire?.size ?? "",
    season: tire?.season ?? "all_season",
    dot_code: asInput(tire?.dot_code),
    condition: tire?.condition ?? (tire ? "" : "new"),
    purchase_date: asInput(tire?.purchase_date),
    price: asInput(tire?.price),
    tread_depth_mm: asInput(tire?.tread_depth_mm),
    pressure_notes: asInput(tire?.pressure_notes),
    notes: asInput(tire?.notes),
    position: "",
    installed_date: todayIso(),
    installed_mileage: String(format.toUnit(vehicle.current_mileage)),
  });
  const errors = form.formState.errors;

  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    ({ position, installed_date, installed_mileage, ...values }) => {
      const path = { vehicle_id: vehicle.id };
      if (tire) {
        return unwrap(
          api.PATCH("/api/v1/vehicles/{vehicle_id}/tires/{tire_id}", {
            params: { path: { ...path, tire_id: tire.id } },
            body: values,
          }),
        );
      }
      return unwrap(
        api.POST("/api/v1/vehicles/{vehicle_id}/tires", {
          params: { path },
          body: {
            ...values,
            position,
            installed_date: position ? installed_date : null,
            installed_mileage:
              position && installed_mileage !== null ? format.toKm(installed_mileage) : null,
          },
        }),
      );
    },
    { successMessage: tire ? t("tires.updated") : t("tires.added"), onSuccess: onClose },
  );

  return (
    <FormDialog
      size="lg"
      title={tire ? t("tires.editTitle") : t("tires.addTitle")}
      submitLabel={tire ? t("common.saveChanges") : t("tires.add")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <FieldRow columns={3}>
        <Field label={t("parts.fields.brand")} error={errors.brand?.message}>
          {(props) => <Input placeholder="Michelin" {...props} {...form.register("brand")} />}
        </Field>
        <Field label={t("tires.fields.model")} optional error={errors.model?.message}>
          {(props) => <Input {...props} {...form.register("model")} />}
        </Field>
        <Field label={t("tires.fields.size")} error={errors.size?.message}>
          {(props) => (
            <Input dir="ltr" placeholder="195/55 R16 87H" {...props} {...form.register("size")} />
          )}
        </Field>
      </FieldRow>
      <FieldRow columns={3}>
        <Field label={t("tires.fields.season")} error={errors.season?.message}>
          {(props) => (
            <Select {...props} {...form.register("season")}>
              {TIRE_SEASONS.map((season) => (
                <option key={season} value={season}>
                  {t(`enums.tireSeason.${season}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("tires.fields.condition")} optional error={errors.condition?.message}>
          {(props) => (
            <Select {...props} {...form.register("condition")}>
              <option value="">{t("common.notSet")}</option>
              {TIRE_CONDITIONS.map((condition) => (
                <option key={condition} value={condition}>
                  {t(`enums.tireCondition.${condition}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field
          label={t("tires.fields.dot")}
          optional
          hint={t("tires.fields.dotHint")}
          error={errors.dot_code?.message}
        >
          {(props) => <Input dir="ltr" {...props} {...form.register("dot_code")} />}
        </Field>
      </FieldRow>
      <FieldRow columns={3}>
        <Field label={t("tires.fields.tread")} optional error={errors.tread_depth_mm?.message}>
          {(props) => <Input inputMode="decimal" {...props} {...form.register("tread_depth_mm")} />}
        </Field>
        <Field
          label={t("vehicles.fields.purchaseDate")}
          optional
          error={errors.purchase_date?.message}
        >
          {(props) => <Input type="date" {...props} {...form.register("purchase_date")} />}
        </Field>
        <Field
          label={t("parts.fields.price", { currency: vehicle.currency })}
          optional
          error={errors.price?.message}
        >
          {(props) => <Input inputMode="decimal" {...props} {...form.register("price")} />}
        </Field>
      </FieldRow>
      {!tire && (
        <FieldRow columns={3}>
          <Field
            label={t("tires.fields.mountAt")}
            optional
            hint={t("tires.fields.mountHint")}
            error={errors.position?.message}
          >
            {(props) => (
              <Select {...props} {...form.register("position")}>
                <option value="">{t("tires.inStorage")}</option>
                {TIRE_POSITIONS.filter((position) => freePositions.includes(position)).map(
                  (position) => (
                    <option key={position} value={position}>
                      {t(`enums.tirePosition.${position}`)}
                    </option>
                  ),
                )}
              </Select>
            )}
          </Field>
          <Field label={t("tires.fields.mountedOn")} error={errors.installed_date?.message}>
            {(props) => <Input type="date" {...props} {...form.register("installed_date")} />}
          </Field>
          <Field
            label={t("common.mileageIn", { unit: format.unitLabel })}
            optional
            error={errors.installed_mileage?.message}
          >
            {(props) => (
              <Input inputMode="numeric" {...props} {...form.register("installed_mileage")} />
            )}
          </Field>
        </FieldRow>
      )}
      <Field label={t("tires.fields.pressure")} optional error={errors.pressure_notes?.message}>
        {(props) => (
          <Input
            placeholder={t("tires.fields.pressurePlaceholder")}
            {...props}
            {...form.register("pressure_notes")}
          />
        )}
      </Field>
      <Field label={t("common.notes")} optional error={errors.notes?.message}>
        {(props) => <Textarea rows={2} {...props} {...form.register("notes")} />}
      </Field>
    </FormDialog>
  );
}
