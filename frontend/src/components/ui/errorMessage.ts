import type { TFunction } from "i18next";

import { isApiError, NETWORK_ERROR } from "@/api/errors";

/**
 * Message to show for an error raised by a query or mutation: a translation for known API error
 * codes, otherwise the server's own message.
 */
export function errorMessage(error: unknown, t: TFunction): string {
  if (!isApiError(error)) return t("errors.generic");
  if (error.code === NETWORK_ERROR) return t("errors.network");
  const key = `errors.codes.${error.code}`;
  const translated = t(key as "errors.generic", { defaultValue: "" });
  return translated || error.message;
}
