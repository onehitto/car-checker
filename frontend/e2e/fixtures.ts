import { type APIRequestContext, test as base, expect, type Page } from "@playwright/test";

export interface Account {
  email: string;
  password: string;
  firstName: string;
  /** For API calls that prepare test data. */
  accessToken: string;
}

/** Same key as src/api/session.ts. */
const REFRESH_TOKEN_KEY = "car-checker.refresh-token";

/** Register a fresh account through the API (unique e-mail per test). */
export async function registerAccount(request: APIRequestContext): Promise<Account> {
  const id = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`;
  const account = {
    email: `e2e-${id}@example.com`,
    password: "Logbook-route-2026",
    firstName: "Robin",
  };
  const response = await request.post("/api/v1/auth/register", {
    data: {
      email: account.email,
      password: account.password,
      first_name: account.firstName,
      last_name: "Tester",
      preferred_language: "en",
      preferred_currency: "EUR",
      preferred_distance_unit: "km",
      timezone: "Europe/Paris",
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  const { data } = (await response.json()) as { data: { tokens: { access_token: string } } };
  return { ...account, accessToken: data.tokens.access_token };
}

/**
 * Open the app already signed in: a new session is opened through the API and its refresh token
 * stored like the app does. (Refresh tokens rotate and a reused one revokes its session, so each
 * page gets its own session.)
 */
export async function openSignedIn(page: Page, account: Account, path = "/"): Promise<void> {
  const response = await page.request.post("/api/v1/auth/login", {
    data: { email: account.email, password: account.password },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  const { data } = (await response.json()) as { data: { tokens: { refresh_token: string } } };
  await page.goto("/login");
  await page.evaluate(([key, token]) => localStorage.setItem(key, token), [
    REFRESH_TOKEN_KEY,
    data.tokens.refresh_token,
  ] as const);
  await page.goto(path);
}

/** Call the API as the account (for test data that is not the subject of the test). */
export async function apiPost<T>(
  request: APIRequestContext,
  account: Account,
  path: string,
  data: object,
): Promise<T> {
  const response = await request.post(path, {
    data,
    headers: { Authorization: `Bearer ${account.accessToken}` },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return ((await response.json()) as { data: T }).data;
}

/**
 * `account` is shared by the tests of a run (registration is rate limited to a few per minute);
 * tests create their own vehicles. `freshAccount` is for tests that change the profile.
 */
export const test = base.extend<{ freshAccount: Account }, { account: Account }>({
  account: [
    async ({ playwright }, provide) => {
      const request = await playwright.request.newContext({
        baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
      });
      await provide(await registerAccount(request));
      await request.dispose();
    },
    { scope: "worker" },
  ],
  freshAccount: async ({ request }, provide) => {
    await provide(await registerAccount(request));
  },
});

export { expect };
