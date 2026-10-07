import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import type { Part, Vehicle } from "@/api/types";
import { Field, FieldRow, FormDialog, Input } from "@/components/ui";
import { todayIso } from "@/lib/format";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useFormat } from "@/lib/useFormat";
import { field } from "@/lib/validation";

const schema = z.object({
  removed_date: field.date(),
  removed_mileage: field.optionalInt(0, 2_000_000),
});

/** The part was taken off (replaced or removed): its lifetime alerts stop. */
export function RemovePartDialog({
  vehicle,
  part,
  onClose,
}: {
  vehicle: Vehicle;
  part: Part;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const format = useFormat();
  const form = useZodForm(schema, {
    removed_date: todayIso(),
    removed_mileage: String(format.toUnit(vehicle.current_mileage)),
  });
  const errors = form.formState.errors;
  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (values) =>
      unwrap(
        api.PATCH("/api/v1/vehicles/{vehicle_id}/parts/{part_id}", {
          params: { path: { vehicle_id: vehicle.id, part_id: part.id } },
          body: {
            removed_date: values.removed_date,
            removed_mileage:
              values.removed_mileage === null ? null : format.toKm(values.removed_mileage),
          },
        }),
      ),
    { successMessage: t("parts.removed"), onSuccess: onClose },
  );
  return (
    <FormDialog
      title={t("parts.removeTitle", { name: part.part_name })}
      description={t("parts.removeBody")}
      submitLabel={t("parts.remove")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <FieldRow>
        <Field label={t("common.date")} error={errors.removed_date?.message}>
          {(props) => <Input type="date" {...props} {...form.register("removed_date")} />}
        </Field>
        <Field
          label={t("common.mileageIn", { unit: format.unitLabel })}
          optional
          error={errors.removed_mileage?.message}
        >
          {(props) => (
            <Input inputMode="numeric" {...props} {...form.register("removed_mileage")} />
          )}
        </Field>
      </FieldRow>
    </FormDialog>
  );
}
