import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { MAINTENANCE_CATEGORIES, PART_CATEGORIES } from "@/api/enums";
import type { MaintenanceType, PartType } from "@/api/types";
import { Field, FieldRow, FormDialog, Input, Select, Textarea } from "@/components/ui";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useFormat } from "@/lib/useFormat";
import { asInput, field } from "@/lib/validation";

const schema = z.object({
  name: field.text(100),
  category: z.string().min(1),
  description: field.optionalText(10_000),
  every_km: field.optionalPositiveInt(1_000_000),
  every_months: field.optionalPositiveInt(240),
});

type TypeFormProps =
  | { kind: "maintenance"; type?: MaintenanceType; onClose: () => void }
  | { kind: "part"; type?: PartType; onClose: () => void };

/** A custom maintenance or part type, with its usual interval (or lifetime). */
export function TypeFormDialog(props: TypeFormProps) {
  const { kind, onClose } = props;
  const { t } = useTranslation();
  const format = useFormat();
  const km =
    props.kind === "maintenance"
      ? props.type?.default_interval_km
      : props.type?.default_lifetime_km;
  const months =
    props.kind === "maintenance"
      ? props.type?.default_interval_months
      : props.type?.default_lifetime_months;
  const form = useZodForm(schema, {
    name: props.type?.name ?? "",
    category: props.type?.category ?? "other",
    description: asInput(props.type?.description),
    every_km: km == null ? "" : String(format.toUnit(km)),
    every_months: asInput(months),
  });
  const errors = form.formState.errors;

  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    ({ every_km, every_months, ...values }): Promise<unknown> => {
      const kmValue = every_km === null ? null : format.toKm(every_km);
      if (props.kind === "maintenance") {
        const body = {
          ...values,
          category: values.category as MaintenanceType["category"],
          default_interval_km: kmValue,
          default_interval_months: every_months,
        };
        return props.type
          ? unwrap(
              api.PATCH("/api/v1/maintenance-types/{type_id}", {
                params: { path: { type_id: props.type.id } },
                body,
              }),
            )
          : unwrap(api.POST("/api/v1/maintenance-types", { body }));
      }
      const body = {
        ...values,
        category: values.category as PartType["category"],
        default_lifetime_km: kmValue,
        default_lifetime_months: every_months,
      };
      return props.type
        ? unwrap(
            api.PATCH("/api/v1/part-types/{type_id}", {
              params: { path: { type_id: props.type.id } },
              body,
            }),
          )
        : unwrap(api.POST("/api/v1/part-types", { body }));
    },
    {
      successMessage: props.type ? t("settings.types.updated") : t("settings.types.added"),
      onSuccess: onClose,
    },
  );

  const categories = kind === "maintenance" ? MAINTENANCE_CATEGORIES : PART_CATEGORIES;
  return (
    <FormDialog
      title={
        props.type
          ? t("settings.types.editTitle")
          : kind === "maintenance"
            ? t("settings.types.addMaintenance")
            : t("settings.types.addPart")
      }
      submitLabel={props.type ? t("common.saveChanges") : t("common.add")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <FieldRow>
        <Field label={t("garages.fields.name")} error={errors.name?.message}>
          {(fieldProps) => <Input {...fieldProps} {...form.register("name")} />}
        </Field>
        <Field label={t("expenses.fields.category")} error={errors.category?.message}>
          {(fieldProps) => (
            <Select {...fieldProps} {...form.register("category")}>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {kind === "maintenance"
                    ? t(`enums.maintenanceCategory.${category as MaintenanceType["category"]}`)
                    : t(`enums.partCategory.${category as PartType["category"]}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </FieldRow>
      <FieldRow>
        <Field
          label={
            kind === "maintenance"
              ? t("schedules.fields.everyDistance", { unit: format.unit })
              : t("parts.fields.lifetimeKm", { unit: format.unit })
          }
          optional
          error={errors.every_km?.message}
        >
          {(fieldProps) => (
            <Input inputMode="numeric" {...fieldProps} {...form.register("every_km")} />
          )}
        </Field>
        <Field
          label={
            kind === "maintenance"
              ? t("schedules.fields.everyMonths")
              : t("parts.fields.lifetimeMonths")
          }
          optional
          error={errors.every_months?.message}
        >
          {(fieldProps) => (
            <Input inputMode="numeric" {...fieldProps} {...form.register("every_months")} />
          )}
        </Field>
      </FieldRow>
      <Field label={t("settings.types.description")} optional error={errors.description?.message}>
        {(fieldProps) => <Textarea rows={2} {...fieldProps} {...form.register("description")} />}
      </Field>
    </FormDialog>
  );
}
