import { isApiError, NETWORK_ERROR } from "@/api/errors";

/** Message to show for an error raised by a query or mutation. */
export function errorMessage(
  error: unknown,
  t: (key: "errors.generic" | "errors.network") => string,
): string {
  if (isApiError(error)) {
    if (error.code === NETWORK_ERROR) return t("errors.network");
    return error.message;
  }
  return t("errors.generic");
}
