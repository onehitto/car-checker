import createClient from "openapi-fetch";

import { ApiError, NETWORK_ERROR, toApiError } from "./errors";
import type { paths } from "./schema";
import { session } from "./session";

/** Endpoints that must not trigger a token refresh when they answer 401. */
const UNAUTHENTICATED_PATHS = [
  "/api/v1/auth/login",
  "/api/v1/auth/register",
  "/api/v1/auth/refresh",
];

function withToken(request: Request): Request {
  const token = session.getAccessToken();
  if (!token) return request;
  const headers = new Headers(request.headers);
  headers.set("Authorization", `Bearer ${token}`);
  return new Request(request, { headers });
}

/** fetch with the bearer token; on 401, refresh once and replay the request. */
export async function authFetch(request: Request): Promise<Response> {
  const replay = request.clone();
  let response: Response;
  try {
    response = await fetch(withToken(request));
  } catch {
    throw new ApiError(0, { code: NETWORK_ERROR, message: "The server cannot be reached." });
  }
  const path = new URL(request.url, window.location.origin).pathname;
  if (response.status !== 401 || UNAUTHENTICATED_PATHS.includes(path)) return response;
  if (!(await session.refresh())) return response;
  return fetch(withToken(replay));
}

export const api = createClient<paths>({ baseUrl: window.location.origin, fetch: authFetch });

interface FetchResult<D> {
  data?: D;
  error?: unknown;
  response: Response;
}

/** Return the `data` of a success envelope or throw an ApiError. */
export async function unwrap<D extends { data: unknown }>(
  request: Promise<FetchResult<D>>,
): Promise<D["data"]> {
  const { data, error, response } = await request;
  if (error !== undefined || data === undefined) throw toApiError(response.status, error);
  return data.data;
}

export interface Page<T> {
  items: T[];
  meta: { page: number; limit: number; total: number; total_pages: number };
}

/** Return the items and metadata of a paginated envelope or throw an ApiError. */
export async function unwrapPage<T, D extends { data: T[]; meta: Page<T>["meta"] }>(
  request: Promise<FetchResult<D>>,
): Promise<Page<D["data"][number]>> {
  const { data, error, response } = await request;
  if (error !== undefined || data === undefined) throw toApiError(response.status, error);
  return { items: data.data, meta: data.meta };
}

/** For 204 No Content endpoints. */
export async function expectNoContent(request: Promise<FetchResult<unknown>>): Promise<void> {
  const { error, response } = await request;
  if (error !== undefined || !response.ok) throw toApiError(response.status, error);
}
