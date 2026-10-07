/** Locale-aware formatting. Distances are stored in km and converted for display. */

const KM_PER_MILE = 1.609344;

export type DistanceUnit = "km" | "mi";

export function toDisplayDistance(km: number, unit: DistanceUnit): number {
  return unit === "mi" ? km / KM_PER_MILE : km;
}

export function toKilometres(value: number, unit: DistanceUnit): number {
  return Math.round(unit === "mi" ? value * KM_PER_MILE : value);
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

/** Today's date as YYYY-MM-DD in the browser's time zone (default for date inputs). */
export function todayIso(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}
