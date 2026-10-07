import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SignedIn } from "@/test/auth";
import { TEST_USER } from "@/test/fixtures";

import { useDueText } from "./useDueText";

function dueText(unit: "km" | "mi" = "km") {
  const { result } = renderHook(() => useDueText(), {
    wrapper: ({ children }) => (
      <SignedIn user={{ ...TEST_USER, preferred_distance_unit: unit }}>{children}</SignedIn>
    ),
  });
  return result.current;
}

describe("useDueText", () => {
  it("says what is left, whichever comes first", () => {
    expect(dueText()({ status: "ok", remaining_km: 3390, remaining_days: 165 })).toBe(
      "in 3,390 km or 165 days",
    );
    expect(dueText()({ status: "due_soon", remaining_km: null, remaining_days: 1 })).toBe(
      "in 1 day",
    );
  });

  it("says how late an overdue item is", () => {
    expect(
      dueText()({ status: "overdue", remaining_km: -1200, overdue_km: 1200, overdue_days: 25 }),
    ).toBe("1,200 km and 25 days overdue");
    // Reminders only have negative remaining values.
    expect(dueText()({ status: "overdue", remaining_days: -3 })).toBe("3 days overdue");
  });

  it("handles due items and missing references", () => {
    expect(dueText()({ status: "due", remaining_km: 0, remaining_days: 0 })).toBe("Due now");
    expect(dueText()({ status: "due", remaining_days: 5 })).toBe("in 5 days");
    expect(dueText()({ status: "unknown" })).toMatch(/No reference yet/);
  });

  it("uses the user's distance unit", () => {
    expect(dueText("mi")({ status: "ok", remaining_km: 1609 })).toBe("in 1,000 mi");
  });
});
