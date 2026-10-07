import { useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { isApiError } from "@/api/errors";
import type { Vehicle } from "@/api/types";
import { Checkbox, Field, FieldRow, FormDialog, Input, Textarea } from "@/components/ui";
import { todayIso } from "@/lib/format";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useFormat } from "@/lib/useFormat";
import { field } from "@/lib/validation";

const schema = z.object({
  mileage: field.int(0, 2_000_000),
  recorded_on: field.date(),
  notes: field.optionalText(10_000),
  force: z.boolean(),
});

/** New odometer reading. A lower reading needs confirmation (odometer replaced or reset). */
export function MileageDialog({ vehicle, onClose }: { vehicle: Vehicle; onClose: () => void }) {
  const { t } = useTranslation();
  const format = useFormat();
  const form = useZodForm(schema, {
    mileage: "",
    recorded_on: todayIso(),
    notes: "",
    force: false,
  });
  const errors = form.formState.errors;
  const force = useWatch({ control: form.control, name: "force" });

  const { onSubmit, pending, formError, mutation } = useFormSubmit(
    form,
    (values) =>
      unwrap(
        api.POST("/api/v1/vehicles/{vehicle_id}/mileage", {
          params: { path: { vehicle_id: vehicle.id } },
          body: { ...values, mileage: format.toKm(values.mileage) },
        }),
      ),
    { successMessage: t("mileage.saved"), onSuccess: onClose },
  );
  const decreased = isApiError(mutation.error) && mutation.error.code === "MILEAGE_DECREASE";

  return (
    <FormDialog
      title={t("mileage.updateTitle")}
      description={t("mileage.current", { distance: format.distance(vehicle.current_mileage) })}
      submitLabel={t("mileage.save")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <FieldRow>
        <Field
          label={t("mileage.reading", { unit: format.unitLabel })}
          error={errors.mileage?.message}
        >
          {(props) => (
            <Input inputMode="numeric" autoFocus {...props} {...form.register("mileage")} />
          )}
        </Field>
        <Field label={t("common.date")} error={errors.recorded_on?.message}>
          {(props) => <Input type="date" {...props} {...form.register("recorded_on")} />}
        </Field>
      </FieldRow>
      {(decreased || force) && <Checkbox label={t("mileage.force")} {...form.register("force")} />}
      <Field label={t("common.notes")} optional error={errors.notes?.message}>
        {(props) => <Textarea rows={2} {...props} {...form.register("notes")} />}
      </Field>
    </FormDialog>
  );
}
