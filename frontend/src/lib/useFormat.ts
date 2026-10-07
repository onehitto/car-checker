import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "@/features/auth/authContext";
import { FORMAT_LOCALES, isLanguage } from "@/i18n";

import {
  type ConsumptionUnit,
  convertConsumption,
  type DistanceUnit,
  formatDate,
  formatDateTime,
  formatDistance,
  formatMoney,
  formatNumber,
  toDisplayDistance,
  toKilometres,
} from "./format";

/** Formatters bound to the interface language and the user's distance unit. */
export function useFormat() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const locale = FORMAT_LOCALES[isLanguage(i18n.language) ? i18n.language : "en"];
  const unit: DistanceUnit = user?.preferred_distance_unit === "mi" ? "mi" : "km";
  const consumptionUnit: ConsumptionUnit = user?.preferred_consumption_unit ?? "l_100km";
  const consumptionLabel = t(`units.consumption.${consumptionUnit}`);

  return useMemo(
    () => ({
      locale,
      unit,
      date: (iso: string | null | undefined) => (iso ? formatDate(locale, iso) : "—"),
      dateTime: (iso: string | null | undefined) => (iso ? formatDateTime(locale, iso) : "—"),
      number: (value: number, digits = 0) => formatNumber(locale, value, digits),
      money: (amount: string | number | null | undefined, currency: string) =>
        amount === null || amount === undefined ? "—" : formatMoney(locale, amount, currency),
      distance: (km: number | null | undefined) =>
        km === null || km === undefined ? "—" : formatDistance(locale, km, unit),
      consumptionUnit,
      /** Litres per 100 km -> "5.8 L/100 km" in the user's consumption unit. */
      consumption: (litresPer100Km: number | null | undefined) =>
        litresPer100Km === null || litresPer100Km === undefined
          ? "—"
          : `${formatNumber(locale, convertConsumption(litresPer100Km, consumptionUnit), 1)} ${consumptionLabel}`,
      /** Amount per km -> amount per display unit ("0.12 € per km"). */
      perDistance: (amountPerKm: number | null | undefined, currency: string) =>
        amountPerKm === null || amountPerKm === undefined
          ? "—"
          : `${formatMoney(locale, unit === "mi" ? amountPerKm * 1.609344 : amountPerKm, currency)}/${unit}`,
      /** Kilometres -> number in the display unit (for inputs). */
      toUnit: (km: number) => Math.round(toDisplayDistance(km, unit)),
      /** Number typed in the display unit -> kilometres for the API. */
      toKm: (value: number) => toKilometres(value, unit),
    }),
    [locale, unit, consumptionUnit, consumptionLabel],
  );
}
