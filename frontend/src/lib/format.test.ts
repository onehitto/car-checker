import { describe, expect, it } from "vitest";

import {
  convertConsumption,
  formatDate,
  formatDistance,
  formatMoney,
  formatMonth,
  toKilometres,
} from "./format";

const clean = (value: string) => value.replace(/\s/g, " ");

describe("format", () => {
  it("formats distances in the preferred unit", () => {
    expect(clean(formatDistance("en-GB", 98_400, "km"))).toBe("98,400 km");
    expect(clean(formatDistance("fr-FR", 98_400, "km"))).toBe("98 400 km");
    expect(clean(formatDistance("en-GB", 160_934, "mi"))).toBe("100,000 mi");
    expect(formatDistance("ar-MA", 98_400, "km")).toContain("كم");
  });

  it("converts entered miles back to kilometres", () => {
    expect(toKilometres(100, "mi")).toBe(161);
    expect(toKilometres(100, "km")).toBe(100);
  });

  it("formats money with the vehicle currency", () => {
    expect(clean(formatMoney("fr-FR", "1234.5", "EUR"))).toBe("1 234,50 €");
    expect(clean(formatMoney("en-GB", "79.95", "MAD"))).toContain("79.95");
  });

  it("keeps Latin digits for Arabic (Morocco)", () => {
    expect(formatDate("ar-MA", "2026-10-06")).toMatch(/2026/);
  });

  it("formats calendar dates without time-zone shifts", () => {
    expect(formatDate("en-GB", "2026-01-01")).toBe("1 Jan 2026");
  });

  it("converts consumption to the preferred unit", () => {
    expect(convertConsumption(5, "l_100km")).toBe(5);
    expect(convertConsumption(5, "km_l")).toBe(20);
    expect(convertConsumption(5, "mpg_us")).toBeCloseTo(47.04, 2);
    expect(convertConsumption(5, "mpg_uk")).toBeCloseTo(56.5, 1);
  });

  it("names months of statistics", () => {
    expect(formatMonth("en-GB", "2026-09")).toBe("Sept");
    expect(formatMonth("fr-FR", "2026-09", true)).toBe("septembre 2026");
  });
});
