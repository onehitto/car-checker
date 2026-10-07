import type { TFunction } from "i18next";

import { isApiError, NETWORK_ERROR } from "@/api/errors";

/** Translation of an API error code, if the interface has one. */
export function codeMessage(code: string, t: TFunction): string | null {
  const key = `errors.codes.${code}`;
  return t(key as "errors.generic", { defaultValue: "" }) || null;
}

/** User-facing message for any error: translated by code, else the server message. */
export function errorMessage(error: unknown, t: TFunction): string {
  if (!isApiError(error)) return t("errors.generic");
  if (error.code === NETWORK_ERROR) return t("errors.network");
  return codeMessage(error.code, t) ?? error.message;
}
