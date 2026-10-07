import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { EXPENSE_CATEGORIES } from "@/api/enums";
import type { Expense, Vehicle } from "@/api/types";
import { Field, FieldRow, FormDialog, Input, Select, Textarea } from "@/components/ui";
import { todayIso } from "@/lib/format";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useFormat } from "@/lib/useFormat";
import { asInput, field } from "@/lib/validation";

const schema = z.object({
  category: field.choice(EXPENSE_CATEGORIES),
  title: field.text(200),
  amount: field.decimal(),
  expense_date: field.date(),
  mileage: field.optionalInt(0, 2_000_000),
  vendor: field.optionalText(120),
  notes: field.optionalText(10_000),
});

/** Manual expenses only: services, parts and fill-ups keep their own expense in sync. */
export function ExpenseFormDialog({
  vehicle,
  expense,
  onClose,
}: {
  vehicle: Vehicle;
  expense?: Expense;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const format = useFormat();
  const form = useZodForm(schema, {
    category: expense?.category ?? "parking",
    title: expense?.title ?? "",
    amount: asInput(expense?.amount),
    expense_date: expense?.expense_date ?? todayIso(),
    mileage: expense?.mileage != null ? String(format.toUnit(expense.mileage)) : "",
    vendor: asInput(expense?.vendor),
    notes: asInput(expense?.notes),
  });
  const errors = form.formState.errors;

  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (values) => {
      const body = {
        ...values,
        mileage: values.mileage === null ? null : format.toKm(values.mileage),
      };
      const path = { vehicle_id: vehicle.id };
      return expense
        ? unwrap(
            api.PATCH("/api/v1/vehicles/{vehicle_id}/expenses/{expense_id}", {
              params: { path: { ...path, expense_id: expense.id } },
              body,
            }),
          )
        : unwrap(api.POST("/api/v1/vehicles/{vehicle_id}/expenses", { params: { path }, body }));
    },
    {
      successMessage: expense ? t("expenses.updated") : t("expenses.added"),
      onSuccess: onClose,
    },
  );

  return (
    <FormDialog
      title={expense ? t("expenses.editTitle") : t("expenses.addTitle")}
      description={t("expenses.formBody")}
      submitLabel={expense ? t("common.saveChanges") : t("expenses.add")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <FieldRow>
        <Field label={t("expenses.fields.category")} error={errors.category?.message}>
          {(props) => (
            <Select {...props} {...form.register("category")}>
              {EXPENSE_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {t(`enums.expenseCategory.${category}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field
          label={t("expenses.fields.amount", { currency: vehicle.currency })}
          error={errors.amount?.message}
        >
          {(props) => <Input inputMode="decimal" {...props} {...form.register("amount")} />}
        </Field>
      </FieldRow>
      <Field label={t("expenses.fields.title")} error={errors.title?.message}>
        {(props) => (
          <Input
            placeholder={t("expenses.fields.titlePlaceholder")}
            {...props}
            {...form.register("title")}
          />
        )}
      </Field>
      <FieldRow columns={3}>
        <Field label={t("common.date")} error={errors.expense_date?.message}>
          {(props) => <Input type="date" {...props} {...form.register("expense_date")} />}
        </Field>
        <Field
          label={t("common.mileageIn", { unit: format.unitLabel })}
          optional
          error={errors.mileage?.message}
        >
          {(props) => <Input inputMode="numeric" {...props} {...form.register("mileage")} />}
        </Field>
        <Field label={t("expenses.fields.vendor")} optional error={errors.vendor?.message}>
          {(props) => <Input {...props} {...form.register("vendor")} />}
        </Field>
      </FieldRow>
      <Field label={t("common.notes")} optional error={errors.notes?.message}>
        {(props) => <Textarea rows={2} {...props} {...form.register("notes")} />}
      </Field>
    </FormDialog>
  );
}
