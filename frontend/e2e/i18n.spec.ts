import { expect, openSignedIn, test } from "./fixtures";

test("switches the interface to Arabic, right to left", async ({ page, freshAccount: account }) => {
  await openSignedIn(page, account);
  await expect(page.getByRole("heading", { name: `Hello ${account.firstName}` })).toBeVisible();

  await page.getByLabel("Language").selectOption("ar");

  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator("html")).toHaveAttribute("lang", "ar");
  await expect(page.getByRole("link", { name: "لوحة القيادة" })).toBeVisible();

  // The choice is saved in the profile: it survives a new session.
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
});
