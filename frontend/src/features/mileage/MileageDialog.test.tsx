import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SignedIn } from "@/test/auth";
import { TEST_VEHICLE } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { MileageDialog } from "./MileageDialog";

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("MileageDialog", () => {
  it("asks to confirm a lower reading, then sends it with force", async () => {
    const bodies: unknown[] = [];
    const fetchMock = vi.fn(async (request: Request) => {
      bodies.push(await request.clone().json());
      return bodies.length === 1
        ? json(422, {
            success: false,
            error: {
              code: "MILEAGE_DECREASE",
              message: "The mileage is lower than a previous reading.",
              fields: { mileage: "Must be greater than or equal to 98910." },
            },
          })
        : json(201, { success: true, data: { id: "entry", mileage: 1200 } });
    });
    vi.stubGlobal("fetch", fetchMock);
    const onClose = vi.fn();

    renderWithProviders(
      <SignedIn>
        <MileageDialog vehicle={TEST_VEHICLE} onClose={onClose} />
      </SignedIn>,
    );
    expect(screen.getByText("The odometer shows 98,910 km so far.")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Odometer reading (km)"), "1200");
    await userEvent.click(screen.getByRole("button", { name: "Save the reading" }));

    expect(await screen.findByText(/lower than a previous one/)).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText(/odometer was replaced or reset/));
    await userEvent.click(screen.getByRole("button", { name: "Save the reading" }));

    await vi.waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(bodies[0]).toMatchObject({ mileage: 1200, force: false });
    expect(bodies[1]).toMatchObject({ mileage: 1200, force: true });
  });
});
