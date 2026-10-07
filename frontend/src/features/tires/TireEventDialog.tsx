import { useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { TIRE_CONDITIONS, TIRE_EVENT_TYPES, TIRE_POSITIONS } from "@/api/enums";
import type { Tire, Vehicle } from "@/api/types";
import { Field, FieldRow, FormDialog, Input, Select, Textarea } from "@/components/ui";
import { todayIso } from "@/lib/format";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useFormat } from "@/lib/useFormat";
import { field } from "@/lib/validation";

const schema = z.object({
  event_type: field.choice(TIRE_EVENT_TYPES),
  event_date: field.date(),
  mileage: field.optionalInt(0, 2_000_000),
  to_position: field.optionalChoice(TIRE_POSITIONS),
  tread_depth_mm: field.optionalDecimal(1, 2),
  condition: field.optionalChoice(TIRE_CONDITIONS),
  notes: field.optionalText(10_000),
});

/** Inspection, repair, mounting, removal or disposal of one tire. */
export function TireEventDialog({
  vehicle,
  tire,
  freePositions,
  onClose,
}: {
  vehicle: Vehicle;
  tire: Tire;
  freePositions: string[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const format = useFormat();
  const allowed = TIRE_EVENT_TYPES.filter((type) =>
    tire.status === "mounted"
      ? type !== "installed"
      : tire.status === "stored"
        ? type !== "removed"
        : false,
  );
  const form = useZodForm(schema, {
    event_type: allowed[0] ?? "inspected",
    event_date: todayIso(),
    mileage: String(format.toUnit(vehicle.current_mileage)),
    to_position: "",
    tread_depth_mm: "",
    condition: "",
    notes: "",
  });
  const errors = form.formState.errors;
  const eventType = useWatch({ control: form.control, name: "event_type" });

  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (values) =>
      unwrap(
        api.POST("/api/v1/vehicles/{vehicle_id}/tires/{tire_id}/events", {
          params: { path: { vehicle_id: vehicle.id, tire_id: tire.id } },
          body: {
            ...values,
            mileage: values.mileage === null ? null : format.toKm(values.mileage),
            to_position: values.event_type === "installed" ? values.to_position : null,
          },
        }),
      ),
    { successMessage: t("tires.eventSaved"), onSuccess: onClose },
  );

  return (
    <FormDialog
      title={t("tires.logTitle", { name: `${tire.brand} ${tire.size}` })}
      submitLabel={t("tires.log")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <FieldRow>
        <Field label={t("tires.fields.event")} error={errors.event_type?.message}>
          {(props) => (
            <Select {...props} {...form.register("event_type")}>
              {allowed.map((type) => (
                <option key={type} value={type}>
                  {t(`enums.tireEvent.${type}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        {eventType === "installed" && (
          <Field label={t("tires.fields.mountAt")} error={errors.to_position?.message}>
            {(props) => (
              <Select {...props} {...form.register("to_position")}>
                <option value="">{t("tires.choosePosition")}</option>
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
        )}
      </FieldRow>
      <FieldRow>
        <Field label={t("common.date")} error={errors.event_date?.message}>
          {(props) => <Input type="date" {...props} {...form.register("event_date")} />}
        </Field>
        <Field
          label={t("common.mileageIn", { unit: format.unit })}
          optional
          error={errors.mileage?.message}
        >
          {(props) => <Input inputMode="numeric" {...props} {...form.register("mileage")} />}
        </Field>
      </FieldRow>
      <FieldRow>
        <Field label={t("tires.fields.tread")} optional error={errors.tread_depth_mm?.message}>
          {(props) => <Input inputMode="decimal" {...props} {...form.register("tread_depth_mm")} />}
        </Field>
        <Field label={t("tires.fields.condition")} optional error={errors.condition?.message}>
          {(props) => (
            <Select {...props} {...form.register("condition")}>
              <option value="">{t("tires.unchanged")}</option>
              {TIRE_CONDITIONS.map((condition) => (
                <option key={condition} value={condition}>
                  {t(`enums.tireCondition.${condition}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </FieldRow>
      <Field label={t("common.notes")} optional error={errors.notes?.message}>
        {(props) => <Textarea rows={2} {...props} {...form.register("notes")} />}
      </Field>
    </FormDialog>
  );
}
