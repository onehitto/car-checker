import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { DOCUMENT_TYPES } from "@/api/enums";
import type { Vehicle, VehicleDocument } from "@/api/types";
import { Field, FieldRow, FormDialog, Input, Select, Textarea } from "@/components/ui";
import { i18n } from "@/i18n";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { asInput, field } from "@/lib/validation";

const DEFAULT_REMINDERS = "30, 7, 1, 0";

/** "30, 7, 1" -> [30, 7, 1]: days before expiry at which to send a reminder. */
const reminderDays = z
  .string()
  .transform((value) =>
    value
      .split(/[\s,;]+/)
      .filter(Boolean)
      .map(Number),
  )
  .refine(
    (days) =>
      days.length <= 10 && days.every((day) => Number.isInteger(day) && day >= 0 && day <= 365),
    { error: () => i18n.t("documents.fields.remindersInvalid") },
  );

const schema = z.object({
  document_type: field.choice(DOCUMENT_TYPES),
  title: field.text(150),
  document_number: field.optionalText(80),
  provider: field.optionalText(120),
  issue_date: field.optionalDate(),
  expiration_date: field.optionalDate(),
  reminder_days: reminderDays,
  notes: field.optionalText(10_000),
});

export function DocumentFormDialog({
  vehicle,
  document,
  onClose,
}: {
  vehicle: Vehicle;
  document?: VehicleDocument;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const form = useZodForm(schema, {
    document_type: document?.document_type ?? "insurance",
    title: document?.title ?? "",
    document_number: asInput(document?.document_number),
    provider: asInput(document?.provider),
    issue_date: asInput(document?.issue_date),
    expiration_date: asInput(document?.expiration_date),
    reminder_days: document ? document.reminder_days.join(", ") : DEFAULT_REMINDERS,
    notes: asInput(document?.notes),
  });
  const errors = form.formState.errors;

  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (body) => {
      const path = { vehicle_id: vehicle.id };
      return document
        ? unwrap(
            api.PATCH("/api/v1/vehicles/{vehicle_id}/documents/{document_id}", {
              params: { path: { ...path, document_id: document.id } },
              body,
            }),
          )
        : unwrap(api.POST("/api/v1/vehicles/{vehicle_id}/documents", { params: { path }, body }));
    },
    {
      successMessage: document ? t("documents.updated") : t("documents.added"),
      onSuccess: onClose,
    },
  );

  return (
    <FormDialog
      size="lg"
      title={document ? t("documents.editTitle") : t("documents.addTitle")}
      description={t("documents.formBody")}
      submitLabel={document ? t("common.saveChanges") : t("documents.add")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <FieldRow>
        <Field label={t("documents.fields.type")} error={errors.document_type?.message}>
          {(props) => (
            <Select {...props} {...form.register("document_type")}>
              {DOCUMENT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`enums.documentType.${type}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("documents.fields.title")} error={errors.title?.message}>
          {(props) => (
            <Input
              placeholder={t("documents.fields.titlePlaceholder")}
              {...props}
              {...form.register("title")}
            />
          )}
        </Field>
      </FieldRow>
      <FieldRow>
        <Field
          label={t("documents.fields.number")}
          optional
          error={errors.document_number?.message}
        >
          {(props) => <Input dir="ltr" {...props} {...form.register("document_number")} />}
        </Field>
        <Field label={t("documents.fields.provider")} optional error={errors.provider?.message}>
          {(props) => <Input {...props} {...form.register("provider")} />}
        </Field>
      </FieldRow>
      <FieldRow>
        <Field label={t("documents.fields.issued")} optional error={errors.issue_date?.message}>
          {(props) => <Input type="date" {...props} {...form.register("issue_date")} />}
        </Field>
        <Field
          label={t("documents.fields.expires")}
          optional
          hint={t("documents.fields.expiresHint")}
          error={errors.expiration_date?.message}
        >
          {(props) => <Input type="date" {...props} {...form.register("expiration_date")} />}
        </Field>
      </FieldRow>
      <Field
        label={t("documents.fields.reminders")}
        hint={t("documents.fields.remindersHint")}
        error={errors.reminder_days?.message}
      >
        {(props) => <Input dir="ltr" {...props} {...form.register("reminder_days")} />}
      </Field>
      <Field label={t("common.notes")} optional error={errors.notes?.message}>
        {(props) => <Textarea rows={2} {...props} {...form.register("notes")} />}
      </Field>
    </FormDialog>
  );
}
