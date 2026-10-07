import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { authFetch, unwrap } from "./client";
import { ApiError } from "./errors";
import { session } from "./session";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("authFetch", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    session.setTokens({ access_token: "old-access", refresh_token: "refresh-1" });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
    session.clear();
  });

  it("sends the bearer token", async () => {
    fetchMock.mockResolvedValueOnce(json(200, { success: true, data: {} }));
    await authFetch(new Request("http://localhost/api/v1/users/me"));
    const sent = fetchMock.mock.calls[0]?.[0] as Request;
    expect(sent.headers.get("Authorization")).toBe("Bearer old-access");
  });

  it("refreshes once and replays the request after a 401", async () => {
    fetchMock
      .mockResolvedValueOnce(
        json(401, { success: false, error: { code: "TOKEN_EXPIRED", message: "x" } }),
      )
      .mockResolvedValueOnce(
        json(200, {
          success: true,
          data: { access_token: "new-access", refresh_token: "refresh-2" },
        }),
      )
      .mockResolvedValueOnce(json(200, { success: true, data: { id: 1 } }));

    const response = await authFetch(new Request("http://localhost/api/v1/vehicles"));
    expect(response.status).toBe(200);
    const replayed = fetchMock.mock.calls[2]?.[0] as Request;
    expect(replayed.headers.get("Authorization")).toBe("Bearer new-access");
    expect(localStorage.getItem("car-checker.refresh-token")).toBe("refresh-2");
  });

  it("signs out when the refresh token is rejected", async () => {
    const listener = vi.fn();
    const unsubscribe = session.subscribe(listener);
    fetchMock
      .mockResolvedValueOnce(
        json(401, { success: false, error: { code: "TOKEN_EXPIRED", message: "x" } }),
      )
      .mockResolvedValueOnce(
        json(401, { success: false, error: { code: "INVALID_TOKEN", message: "x" } }),
      );

    const response = await authFetch(new Request("http://localhost/api/v1/vehicles"));
    expect(response.status).toBe(401);
    expect(session.hasRefreshToken()).toBe(false);
    expect(listener).toHaveBeenCalledWith(false);
    unsubscribe();
  });

  it("never refreshes for the login endpoint", async () => {
    fetchMock.mockResolvedValueOnce(
      json(401, { success: false, error: { code: "INVALID_CREDENTIALS", message: "x" } }),
    );
    await authFetch(new Request("http://localhost/api/v1/auth/login", { method: "POST" }));
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("unwrap", () => {
  it("returns the envelope data", async () => {
    const result = await unwrap(
      Promise.resolve({ data: { success: true, data: { id: "a" } }, response: new Response() }),
    );
    expect(result).toEqual({ id: "a" });
  });

  it("throws an ApiError with field messages", async () => {
    const failing = unwrap(
      Promise.resolve({
        error: {
          success: false,
          error: { code: "VALIDATION_ERROR", message: "Invalid", fields: { mileage: "Too low" } },
        },
        response: new Response(null, { status: 422 }),
      }),
    );
    await expect(failing).rejects.toMatchObject({
      status: 422,
      code: "VALIDATION_ERROR",
      fields: { mileage: "Too low" },
    });
    await expect(failing).rejects.toBeInstanceOf(ApiError);
  });
});
