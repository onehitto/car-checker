import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { FuelRecord } from "@/api/types";
import { SignedIn } from "@/test/auth";
import { TEST_VEHICLE } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { FuelFormDialog } from "./FuelFormDialog";

const RECORD: FuelRecord = {
  id: "00000000-0000-7000-8000-000000000010",
  vehicle_id: TEST_VEHICLE.id,
  fill_date: "2026-09-17",
  mileage: 98510,
  liters: "46.500",
  price_per_liter: "1.7900",
  total_price: "83.24",
  full_tank: true,
  missed_previous: false,
  fuel_type: "petrol",
  gas_station: "Shell",
  notes: null,
  distance_since_previous: 730,
  consumption_l_100km: 6.37,
  created_by_id: null,
  created_at: "2026-09-17T10:00:00Z",
  updated_at: "2026-09-17T10:00:00Z",
};

afterEach(() => vi.unstubAllGlobals());

async function editAndSave(change: (user: ReturnType<typeof userEvent.setup>) => Promise<void>) {
  const bodies: Record<string, unknown>[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: Request) => {
      bodies.push(await request.clone().json());
      return new Response(JSON.stringify({ success: true, data: RECORD }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  const onClose = vi.fn();
  renderWithProviders(
    <SignedIn>
      <FuelFormDialog vehicle={TEST_VEHICLE} record={RECORD} onClose={onClose} />
    </SignedIn>,
  );
  const user = userEvent.setup();
  await change(user);
  await user.click(screen.getByRole("button", { name: "Save changes" }));
  await vi.waitFor(() => expect(onClose).toHaveBeenCalled());
  return bodies[0]!;
}

describe("FuelFormDialog", () => {
  it("keeps the amount paid when only the litres change", async () => {
    const body = await editAndSave(async (user) => {
      await user.clear(screen.getByLabelText("Litres"));
      await user.type(screen.getByLabelText("Litres"), "47");
    });
    expect(body).toMatchObject({ liters: "47", price_per_liter: null, total_price: "83.24" });
  });

  it("recomputes the total when the price per litre changes", async () => {
    const body = await editAndSave(async (user) => {
      await user.clear(screen.getByLabelText(/^Price per litre/));
      await user.type(screen.getByLabelText(/^Price per litre/), "1,85");
    });
    expect(body).toMatchObject({ price_per_liter: "1.85", total_price: null });
  });
});
