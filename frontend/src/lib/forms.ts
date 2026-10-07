import type { TFunction } from "i18next";
import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

import { isApiError } from "@/api/errors";
import { errorMessage } from "@/components/ui/errorMessage";

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
  let unmatched = entries.length === 0;
  for (const [field, message] of entries) {
    if (fieldNames.includes(field)) setError(field as Path<T>, { type: "server", message });
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
