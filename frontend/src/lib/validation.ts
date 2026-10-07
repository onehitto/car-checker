/**
 * Form field schemas. Inputs hold strings; these schemas trim them, turn blanks into null and
 * parse numbers, so the parsed values match the API request bodies.
 */
import { z } from "zod";

import { FORMAT_LOCALES, i18n, isLanguage } from "@/i18n";

function formatBound(value: number | bigint): string {
  const locale = FORMAT_LOCALES[isLanguage(i18n.language) ? i18n.language : "en"];
  return new Intl.NumberFormat(locale).format(value);
}

function isBlank(input: unknown): boolean {
  return input === undefined || input === null || input === "";
}

// Messages are looked up when validation runs, so they follow the current language.
z.config({
  customError: (issue) => {
    if (isBlank(issue.input)) return i18n.t("validation.required");
    switch (issue.code) {
      case "invalid_type":
        if (issue.expected === "int") return i18n.t("validation.wholeNumber");
        return issue.expected === "number" ? i18n.t("validation.number") : undefined;
      case "too_small":
        if (issue.origin === "string") return i18n.t("validation.required");
        if (issue.origin === "number")
          return issue.inclusive === false
            ? i18n.t("validation.positive")
            : i18n.t("validation.min", { min: formatBound(issue.minimum) });
        return undefined;
      case "too_big":
        if (issue.origin === "string")
          return i18n.t("validation.maxLength", { count: Number(issue.maximum) });
        if (issue.origin === "number")
          return i18n.t("validation.max", { max: formatBound(issue.maximum) });
        return undefined;
      case "invalid_format":
        return issue.format === "email" ? i18n.t("validation.email") : i18n.t("validation.invalid");
      case "not_multiple_of":
        return i18n.t("validation.wholeNumber");
      default:
        return undefined;
    }
  },
});

const blankToNull = (value: string) => (value === "" ? null : value);
const toNumber = (value: string) => {
  const trimmed = value.trim();
  return trimmed === "" ? null : Number(trimmed.replace(",", "."));
};

const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** Decimal kept as a string (exact amounts); a comma is accepted as decimal separator. */
function decimalPattern(places: number, digits: number): z.ZodString {
  const pattern = new RegExp(`^\\d{1,${digits}}(\\.\\d{1,${places}})?$`);
  return z.string().regex(pattern, {
    error: () => i18n.t("validation.decimal", { count: places }),
  });
}

export const field = {
  text: (max: number) => z.string().trim().min(1).max(max),
  optionalText: (max: number) => z.string().trim().max(max).transform(blankToNull),
  email: () => z.string().trim().pipe(z.email()),
  int: (min: number, max: number) =>
    z.string().transform(toNumber).pipe(z.number().int().min(min).max(max)),
  optionalInt: (min: number, max: number) =>
    z.string().transform(toNumber).pipe(z.number().int().min(min).max(max).nullable()),
  /** Strictly positive integer (intervals, lifetimes). */
  optionalPositiveInt: (max: number) =>
    z.string().transform(toNumber).pipe(z.number().int().gt(0).max(max).nullable()),
  decimal: (places = 2, digits = 10) =>
    z
      .string()
      .trim()
      .min(1)
      .transform((value) => value.replace(",", "."))
      .pipe(decimalPattern(places, digits)),
  optionalDecimal: (places = 2, digits = 10) =>
    z
      .string()
      .trim()
      .transform((value) => blankToNull(value.replace(",", ".")))
      .pipe(decimalPattern(places, digits).nullable()),
  date: () => z.string().regex(DATE),
  optionalDate: () => z.string().transform(blankToNull).pipe(z.string().regex(DATE).nullable()),
  /** Select whose empty option means "none". */
  optionalChoice: <const T extends readonly [string, ...string[]]>(values: T) =>
    z
      .enum(values)
      .or(z.literal(""))
      .transform((value) => (value === "" ? null : value)),
  choice: <const T extends readonly [string, ...string[]]>(values: T) => z.enum(values),
  /** Select of ids (garages, types...); empty means none. */
  optionalId: () => z.string().transform(blankToNull),
  id: () => z.string().min(1),
};

/** Value of a nullable API field as an input string. */
export function asInput(value: string | number | null | undefined): string {
  return value === null || value === undefined ? "" : String(value);
}
