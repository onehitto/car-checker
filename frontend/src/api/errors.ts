/** Errors raised by the API client. The backend always answers errors with this envelope:
 * {"success": false, "error": {"code", "message", "fields", "request_id"}} */

export interface ApiErrorBody {
  code: string;
  message: string;
  fields?: Record<string, string> | null;
  request_id?: string | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: Record<string, string>;
  readonly requestId: string | null;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.fields = body.fields ?? {};
    this.requestId = body.request_id ?? null;
  }
}

export const NETWORK_ERROR = "NETWORK_ERROR";

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

function isErrorEnvelope(value: unknown): value is { error: ApiErrorBody } {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const error = (value as { error: unknown }).error;
  return typeof error === "object" && error !== null && "code" in error && "message" in error;
}

export function toApiError(status: number, body: unknown): ApiError {
  if (isErrorEnvelope(body)) return new ApiError(status, body.error);
  return new ApiError(status, {
    code: status >= 500 ? "INTERNAL_ERROR" : "HTTP_ERROR",
    message: `Unexpected response from the server (${status}).`,
  });
}
