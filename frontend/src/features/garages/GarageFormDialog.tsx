import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { GARAGE_TYPES } from "@/api/enums";
import type { Garage } from "@/api/types";
import { Field, FieldRow, FormDialog, Input, Select, Textarea } from "@/components/ui";
import { i18n } from "@/i18n";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { asInput, field } from "@/lib/validation";

const PHONE = /^\+?[0-9 ().-]{6,32}$/;
const WEBSITE = /^https?:\/\/\S+$/;

const schema = z.object({
  name: field.text(120),
  garage_type: field.choice(GARAGE_TYPES),
  contact_name: field.optionalText(120),
  phone: field.optionalText(32).pipe(
    z
      .string()
      .regex(PHONE, { error: () => i18n.t("garages.fields.phoneInvalid") })
      .nullable(),
  ),
  email: field.optionalText(254).pipe(z.email().nullable()),
  address: field.optionalText(255),
  city: field.optionalText(100),
  country: field.optionalText(100),
  website: field
    .optionalText(255)
    // "atlas.ma" is understood as "https://atlas.ma".
    .transform((value) => (value && !/^https?:\/\//i.test(value) ? `https://${value}` : value))
    .pipe(
      z
        .string()
        .regex(WEBSITE, { error: () => i18n.t("garages.fields.websiteInvalid") })
        .nullable(),
    ),
  notes: field.optionalText(10_000),
});

export function GarageFormDialog({ garage, onClose }: { garage?: Garage; onClose: () => void }) {
  const { t } = useTranslation();
  const form = useZodForm(schema, {
    name: garage?.name ?? "",
    garage_type: garage?.garage_type ?? "garage",
    contact_name: asInput(garage?.contact_name),
    phone: asInput(garage?.phone),
    email: asInput(garage?.email),
    address: asInput(garage?.address),
    city: asInput(garage?.city),
    country: asInput(garage?.country),
    website: asInput(garage?.website),
    notes: asInput(garage?.notes),
  });
  const errors = form.formState.errors;
  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (body) =>
      garage
        ? unwrap(
            api.PATCH("/api/v1/garages/{garage_id}", {
              params: { path: { garage_id: garage.id } },
              body,
            }),
          )
        : unwrap(api.POST("/api/v1/garages", { body })),
    { successMessage: garage ? t("garages.updated") : t("garages.added"), onSuccess: onClose },
  );

  return (
    <FormDialog
      size="lg"
      title={garage ? t("garages.editTitle") : t("garages.addTitle")}
      submitLabel={garage ? t("common.saveChanges") : t("garages.add")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <FieldRow>
        <Field label={t("garages.fields.name")} error={errors.name?.message}>
          {(props) => <Input {...props} {...form.register("name")} />}
        </Field>
        <Field label={t("garages.fields.type")} error={errors.garage_type?.message}>
          {(props) => (
            <Select {...props} {...form.register("garage_type")}>
              {GARAGE_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`enums.garageType.${type}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </FieldRow>
      <FieldRow columns={3}>
        <Field label={t("garages.fields.contact")} optional error={errors.contact_name?.message}>
          {(props) => <Input {...props} {...form.register("contact_name")} />}
        </Field>
        <Field label={t("garages.fields.phone")} optional error={errors.phone?.message}>
          {(props) => <Input type="tel" dir="ltr" {...props} {...form.register("phone")} />}
        </Field>
        <Field label={t("auth.email")} optional error={errors.email?.message}>
          {(props) => <Input type="email" dir="ltr" {...props} {...form.register("email")} />}
        </Field>
      </FieldRow>
      <Field label={t("garages.fields.address")} optional error={errors.address?.message}>
        {(props) => <Input {...props} {...form.register("address")} />}
      </Field>
      <FieldRow columns={3}>
        <Field label={t("garages.fields.city")} optional error={errors.city?.message}>
          {(props) => <Input {...props} {...form.register("city")} />}
        </Field>
        <Field label={t("garages.fields.country")} optional error={errors.country?.message}>
          {(props) => <Input {...props} {...form.register("country")} />}
        </Field>
        <Field label={t("garages.fields.website")} optional error={errors.website?.message}>
          {(props) => (
            <Input
              type="url"
              dir="ltr"
              placeholder="https://"
              {...props}
              {...form.register("website")}
            />
          )}
        </Field>
      </FieldRow>
      <Field label={t("common.notes")} optional error={errors.notes?.message}>
        {(props) => <Textarea rows={2} {...props} {...form.register("notes")} />}
      </Field>
    </FormDialog>
  );
}
