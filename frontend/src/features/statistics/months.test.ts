import { describe, expect, it } from "vitest";

import { fillMonths } from "./months";

describe("fillMonths", () => {
  it("adds the months without expenses between the first and the last", () => {
    expect(
      fillMonths([
        { month: "2025-11", total: "40.00" },
        { month: "2026-02", total: "10.50" },
      ]),
    ).toEqual([
      { month: "2025-11", total: 40 },
      { month: "2025-12", total: 0 },
      { month: "2026-01", total: 0 },
      { month: "2026-02", total: 10.5 },
    ]);
  });

  it("handles empty and single-month series", () => {
    expect(fillMonths([])).toEqual([]);
    expect(fillMonths([{ month: "2026-03", total: "5" }])).toEqual([
      { month: "2026-03", total: 5 },
    ]);
  });
});
