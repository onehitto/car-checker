import { expect, test } from "./fixtures";

test("sends signed-out visitors to sign in, then back where they were going", async ({
  page,
  account,
}) => {
  await page.goto("/vehicles");
  await expect(page).toHaveURL(/\/login\?next=%2Fvehicles/);

  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Password").fill(account.password);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/vehicles$/);
  await expect(page.getByRole("heading", { name: "Vehicles", level: 1 })).toBeVisible();
});

test("refuses a wrong password with a clear message", async ({ page, account }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Password").fill("Not-the-password-1");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toHaveText("Wrong email or password.");
});

test("signs out", async ({ page, account }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Password").fill(account.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: `Hello ${account.firstName}` })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
});
