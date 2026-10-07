import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { NOTE_CATEGORIES } from "@/api/enums";
import type { Note, Vehicle } from "@/api/types";
import { Checkbox, Field, FieldRow, FormDialog, Input, Select, Textarea } from "@/components/ui";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { asInput, field } from "@/lib/validation";

const schema = z.object({
  title: field.optionalText(200),
  body: field.text(10_000),
  category: field.choice(NOTE_CATEGORIES),
  is_pinned: z.boolean(),
});

export function NoteFormDialog({
  vehicle,
  note,
  onClose,
}: {
  vehicle: Vehicle;
  note?: Note;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const form = useZodForm(schema, {
    title: asInput(note?.title),
    body: note?.body ?? "",
    category: note?.category ?? "general",
    is_pinned: note?.is_pinned ?? false,
  });
  const errors = form.formState.errors;
  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (body) => {
      const path = { vehicle_id: vehicle.id };
      return note
        ? unwrap(
            api.PATCH("/api/v1/vehicles/{vehicle_id}/notes/{note_id}", {
              params: { path: { ...path, note_id: note.id } },
              body,
            }),
          )
        : unwrap(api.POST("/api/v1/vehicles/{vehicle_id}/notes", { params: { path }, body }));
    },
    { successMessage: note ? t("notes.updated") : t("notes.added"), onSuccess: onClose },
  );
  return (
    <FormDialog
      size="lg"
      title={note ? t("notes.editTitle") : t("notes.addTitle")}
      submitLabel={note ? t("common.saveChanges") : t("notes.add")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <FieldRow>
        <Field label={t("notes.fields.title")} optional error={errors.title?.message}>
          {(props) => <Input {...props} {...form.register("title")} />}
        </Field>
        <Field label={t("expenses.fields.category")} error={errors.category?.message}>
          {(props) => (
            <Select {...props} {...form.register("category")}>
              {NOTE_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {t(`enums.noteCategory.${category}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </FieldRow>
      <Field label={t("notes.fields.body")} error={errors.body?.message}>
        {(props) => (
          <Textarea
            rows={6}
            placeholder={t("notes.fields.bodyPlaceholder")}
            {...props}
            {...form.register("body")}
          />
        )}
      </Field>
      <Checkbox label={t("notes.fields.pinned")} {...form.register("is_pinned")} />
    </FormDialog>
  );
}
