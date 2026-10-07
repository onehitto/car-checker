import { apiPost, expect, openSignedIn, test } from "./fixtures";

test("adds a vehicle, updates its mileage and records a service", async ({ page, account }) => {
  await openSignedIn(page, account, "/vehicles/new");

  await page.getByLabel("Brand").fill("Dacia");
  await page.getByLabel("Model").fill("Sandero");
  await page.getByLabel("Year").fill("2020");
  await page.getByLabel("License plate").fill("12-AB-34");
  await page.getByLabel(/^Current mileage/).fill("45000");
  await page.getByRole("button", { name: "Add a vehicle", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Dacia Sandero", level: 1 })).toBeVisible();
  await expect(page.getByRole("img", { name: "Odometer: 45,000 km" })).toBeVisible();

  // A new reading rolls the odometer.
  await page.getByRole("button", { name: "Update mileage" }).click();
  await page.getByLabel(/^Odometer reading/).fill("45250");
  await page.getByRole("button", { name: "Save the reading" }).click();
  await expect(page.getByText("Mileage updated")).toBeVisible();
  await expect(page.getByRole("img", { name: "Odometer: 45,250 km" })).toBeVisible();

  // Record a service from the maintenance tab.
  await page.getByRole("link", { name: "Maintenance", exact: true }).click();
  await page.getByRole("button", { name: "Record a service" }).first().click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Type").selectOption({ label: "Oil change" });
  await dialog.getByLabel(/^Total/).fill("89,90");
  await dialog.getByRole("button", { name: "Record a service" }).click();
  await expect(page.getByText("Service recorded")).toBeVisible();
  const row = page.getByRole("listitem").filter({ hasText: "€89.90" });
  await expect(row).toContainText("Oil change");
  await expect(row).toContainText("45,250 km");

  // The garage dashboard lists the vehicle.
  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page.getByRole("link", { name: "Dacia Sandero" }).first()).toBeVisible();
});

test("shows an overdue schedule and its alert", async ({ page, request, account }) => {
  const vehicle = await apiPost<{ id: string }>(request, account, "/api/v1/vehicles", {
    brand: "Renault",
    model: "Clio",
    year: 2016,
    fuel_type: "petrol",
    initial_mileage: 100000,
  });
  const types = await request.get("/api/v1/maintenance-types", {
    headers: { Authorization: `Bearer ${account.accessToken}` },
  });
  const brakeFluid = (
    (await types.json()) as { data: { id: string; code: string | null }[] }
  ).data.find((type) => type.code === "brake_fluid");
  expect(brakeFluid).toBeDefined();
  await apiPost(request, account, `/api/v1/vehicles/${vehicle.id}/maintenance-schedules`, {
    maintenance_type_id: brakeFluid!.id,
    interval_months: 24,
    last_service_date: "2020-01-15",
  });

  await openSignedIn(page, account, `/vehicles/${vehicle.id}/maintenance/schedules`);
  const schedule = page.getByRole("listitem").filter({ hasText: "Brake fluid" });
  await expect(schedule).toContainText("Overdue");
  await expect(schedule).toContainText("days overdue");

  await page
    .getByRole("link", { name: /^Alerts/ })
    .first()
    .click();
  await expect(page.getByRole("button", { name: "Brake fluid overdue" })).toBeVisible();
});
