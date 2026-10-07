/** Locale-aware formatting. Distances are stored in km and converted for display. */

const KM_PER_MILE = 1.609344;

export type DistanceUnit = "km" | "mi";

export function toDisplayDistance(km: number, unit: DistanceUnit): number {
  return unit === "mi" ? km / KM_PER_MILE : km;
}

export function toKilometres(value: number, unit: DistanceUnit): number {
  return Math.round(unit === "mi" ? value * KM_PER_MILE : value);
}

export type ConsumptionUnit = "l_100km" | "km_l" | "mpg_us" | "mpg_uk";

/** Litres per 100 km (as stored) to the user's consumption unit. */
export function convertConsumption(litresPer100Km: number, unit: ConsumptionUnit): number {
  if (litresPer100Km <= 0) return 0;
  switch (unit) {
    case "l_100km":
      return litresPer100Km;
    case "km_l":
      return 100 / litresPer100Km;
    case "mpg_us":
      return 235.215 / litresPer100Km;
    case "mpg_uk":
      return 282.481 / litresPer100Km;
  }
}

export function formatNumber(locale: string, value: number, digits = 0): string {
  return new Intl.NumberFormat(locale, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

export function formatDistance(locale: string, km: number, unit: DistanceUnit): string {
  return `${formatNumber(locale, Math.round(toDisplayDistance(km, unit)))} ${unit}`;
}

export function formatMoney(locale: string, amount: string | number, currency: string): string {
  const value = typeof amount === "string" ? Number(amount) : amount;
  try {
    return new Intl.NumberFormat(locale, { style: "currency", currency }).format(value);
  } catch {
    return `${formatNumber(locale, value, 2)} ${currency}`;
  }
}

/** Dates from the API are ISO strings (YYYY-MM-DD for calendar dates). */
export function formatDate(locale: string, iso: string): string {
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number);
  const date = new Date(Date.UTC(year ?? 1970, (month ?? 1) - 1, day ?? 1));
  return new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function formatDateTime(locale: string, iso: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(iso),
  );
}

/** "2026-09" -> "Sep" (or "September 2026" when long). */
export function formatMonth(locale: string, month: string, long = false): string {
  const [year, index] = month.split("-").map(Number);
  return new Intl.DateTimeFormat(locale, {
    month: long ? "long" : "short",
    year: long ? "numeric" : undefined,
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year ?? 1970, (index ?? 1) - 1, 1)));
}

/** File sizes: "820 kB", "2.4 MB". */
export function formatBytes(locale: string, bytes: number): string {
  if (bytes < 1000 * 1000) {
    return new Intl.NumberFormat(locale, {
      style: "unit",
      unit: "kilobyte",
      maximumFractionDigits: 0,
    }).format(Math.max(1, bytes / 1000));
  }
  return new Intl.NumberFormat(locale, {
    style: "unit",
    unit: "megabyte",
    maximumFractionDigits: 1,
  }).format(bytes / (1000 * 1000));
}

/** Today's date as YYYY-MM-DD in the browser's time zone (default for date inputs). */
export function todayIso(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}
