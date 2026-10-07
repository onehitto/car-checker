import { describe, expect, it } from "vitest";
import { z } from "zod";

import { field } from "./validation";

function errorOf(schema: z.ZodType, input: unknown): string | undefined {
  const result = schema.safeParse(input);
  return result.success ? undefined : result.error.issues[0]?.message;
}

describe("field schemas", () => {
  it("trims text and requires it", () => {
    expect(field.text(10).parse("  Logan ")).toBe("Logan");
    expect(errorOf(field.text(10), "   ")).toBe("Required");
    expect(errorOf(field.text(3), "abcd")).toBe("3 characters at most.");
  });

  it("turns blank optional values into null", () => {
    expect(field.optionalText(10).parse("  ")).toBeNull();
    expect(field.optionalInt(0, 10).parse("")).toBeNull();
    expect(field.optionalDecimal().parse("")).toBeNull();
    expect(field.optionalDate().parse("")).toBeNull();
    expect(field.optionalChoice(["a", "b"]).parse("")).toBeNull();
  });

  it("parses integers within bounds", () => {
    expect(field.int(0, 2_000_000).parse(" 98400 ")).toBe(98400);
    expect(errorOf(field.int(0, 10), "")).toBe("Required");
    expect(errorOf(field.int(0, 10), "abc")).toBe("Enter a number.");
    expect(errorOf(field.int(0, 10), "2.5")).toBe("Enter a whole number.");
    expect(errorOf(field.int(0, 2_000_000), "3000000")).toBe("Enter 2,000,000 or less.");
    expect(errorOf(field.optionalPositiveInt(100), "0")).toBe("Enter a number greater than 0.");
  });

  it("keeps decimals exact and accepts a comma", () => {
    expect(field.decimal().parse("120,5")).toBe("120.5");
    expect(errorOf(field.decimal(), "")).toBe("Required");
    expect(errorOf(field.decimal(), "12.345")).toBe(
      "Enter a number with at most 2 decimals, e.g. 120.50.",
    );
    expect(field.optionalDecimal(3, 4).parse("45.123")).toBe("45.123");
  });

  it("validates dates and choices", () => {
    expect(field.date().parse("2026-10-07")).toBe("2026-10-07");
    expect(errorOf(field.date(), "")).toBe("Required");
    expect(field.optionalChoice(["a", "b"]).parse("b")).toBe("b");
  });
});
