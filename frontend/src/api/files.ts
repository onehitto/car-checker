/** Multipart uploads and binary downloads (outside the JSON client). */
import { authFetch } from "./client";
import { toApiError } from "./errors";

async function send(request: Request): Promise<Response> {
  const response = await authFetch(request);
  if (!response.ok) throw toApiError(response.status, await response.json().catch(() => null));
  return response;
}

/** Send a FormData body and return the `data` of the success envelope. */
export async function sendForm<T>(
  method: "POST" | "PUT",
  path: string,
  body: FormData,
): Promise<T> {
  const response = await send(new Request(new URL(path, window.location.origin), { method, body }));
  return ((await response.json()) as { data: T }).data;
}

export async function fetchBlob(path: string): Promise<Blob> {
  const response = await send(new Request(new URL(path, window.location.origin)));
  return response.blob();
}

/** Save a protected file: the request carries the bearer token, so a plain link cannot. */
export async function downloadFile(path: string, fileName: string): Promise<void> {
  const url = URL.createObjectURL(await fetchBlob(path));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
