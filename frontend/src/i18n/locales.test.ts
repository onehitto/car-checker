import { describe, expect, it } from "vitest";

import ar from "./locales/ar.json";
import en from "./locales/en.json";
import fr from "./locales/fr.json";

function keys(value: unknown, prefix = ""): string[] {
  if (typeof value !== "object" || value === null) return [prefix];
  return Object.entries(value).flatMap(([key, child]) =>
    keys(child, prefix ? `${prefix}.${key}` : key),
  );
}

/** Arabic has more plural forms than English: compare keys without plural suffixes. */
const base = (key: string) => key.replace(/_(zero|one|two|few|many|other)$/, "");

describe("translations", () => {
  it.each([
    ["fr", fr],
    ["ar", ar],
  ])("%s has every English key", (_, catalog) => {
    const expected = new Set(keys(en).map(base));
    const actual = new Set(keys(catalog).map(base));
    expect([...expected].filter((key) => !actual.has(key))).toEqual([]);
    expect([...actual].filter((key) => !expected.has(key))).toEqual([]);
  });
});
