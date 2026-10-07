import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { useState } from "react";
import {
  type DefaultValues,
  type FieldValues,
  type Path,
  useForm,
  type UseFormReturn,
  type UseFormSetError,
} from "react-hook-form";
import { useTranslation } from "react-i18next";
import type { z } from "zod";

import { isApiError } from "@/api/errors";
import { codeMessage, errorMessage } from "@/components/ui/errorMessage";
import { useToast } from "@/components/ui/toastContext";

/**
 * Show API validation errors next to their inputs. Returns the message to display above the
 * form when the error does not entirely belong to fields of this form, otherwise null.
 */
export function applyServerErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fieldNames: readonly string[],
  t: TFunction,
): string | null {
  if (!isApiError(error)) return errorMessage(error, t);
  const entries = Object.entries(error.fields);
  // A business rule (e.g. MILEAGE_DECREASE) has a translated message; generic validation
  // errors keep the server's per-field text.
  const ruleMessage = error.code === "VALIDATION_ERROR" ? null : codeMessage(error.code, t);
  let unmatched = entries.length === 0;
  for (const [field, message] of entries) {
    if (fieldNames.includes(field))
      setError(field as Path<T>, { type: "server", message: ruleMessage ?? message });
    else unmatched = true;
  }
  return unmatched ? errorMessage(error, t) : null;
}

/** Drop empty optional values so the API applies its defaults. */
export function compact<T extends Record<string, unknown>>(values: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(values).filter(
      ([, value]) => value !== "" && value !== null && value !== undefined,
    ),
  ) as Partial<T>;
}

/** Empty inputs become null (clears the value on PATCH). */
export function emptyToNull<T extends Record<string, unknown>>(values: T): T {
  return Object.fromEntries(
    Object.entries(values).map(([key, value]) => [key, value === "" ? null : value]),
  ) as T;
}

/** react-hook-form bound to a zod schema: inputs are the schema input, submit gets its output. */
export function useZodForm<S extends z.ZodType<FieldValues, FieldValues>>(
  schema: S,
  defaultValues: z.input<S>,
): UseFormReturn<z.input<S>, unknown, z.output<S>> {
  return useForm<z.input<S>, unknown, z.output<S>>({
    resolver: zodResolver(schema as never),
    defaultValues: defaultValues as DefaultValues<z.input<S>>,
  });
}

interface FormSubmitOptions<TResult> {
  /** Toast shown after saving ("Service recorded"). */
  successMessage?: string;
  onSuccess?: (result: TResult) => void;
  /** false: do not refresh the queries on screen afterwards (e.g. the account is gone). */
  invalidate?: boolean;
}

/**
 * Submit a form through a mutation: API field errors go to their inputs, other errors to the
 * returned `formError`, success shows a toast.
 */
export function useFormSubmit<TInput extends FieldValues, TOutput, TResult>(
  form: UseFormReturn<TInput, unknown, TOutput>,
  mutationFn: (values: TOutput) => Promise<TResult>,
  { successMessage, onSuccess, invalidate }: FormSubmitOptions<TResult> = {},
) {
  const { t } = useTranslation();
  const toast = useToast();
  const [formError, setFormError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn,
    meta: { invalidate },
    onSuccess: (result) => {
      if (successMessage) toast.success(successMessage);
      onSuccess?.(result);
    },
    onError: (error) =>
      setFormError(applyServerErrors(error, form.setError, Object.keys(form.getValues()), t)),
  });
  const onSubmit = form.handleSubmit((values) => {
    setFormError(null);
    mutation.mutate(values);
  });
  return { onSubmit, pending: mutation.isPending, formError, mutation };
}
