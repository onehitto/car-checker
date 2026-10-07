import { useTranslation } from "react-i18next";

/** Shared look of the charts: steel ticks on hairline rules, petrol series. */
export const CHART = {
  series: "#0b6e75",
  seriesSoft: "#e3f1f2",
  secondary: "#17212b",
  grid: "#d5dbe0",
  tick: { fill: "#5e6b78", fontSize: 13 },
  font: "inherit",
};

/** Palette for categories (dashboard lamp hues first, then neutrals). */
export const CATEGORY_COLORS = [
  "#0b6e75",
  "#2b6cb0",
  "#b7791f",
  "#c2410c",
  "#2f7d4f",
  "#b42318",
  "#5e6b78",
  "#17212b",
  "#6b8e9b",
  "#9a6b3f",
  "#7c5aa6",
  "#a1a9b1",
  "#3a4856",
];

/** Charts are drawn left to right; in Arabic the time axis runs right to left. */
export function useChartDirection() {
  const { i18n } = useTranslation();
  const rtl = i18n.dir() === "rtl";
  return { rtl, yOrientation: rtl ? ("right" as const) : ("left" as const) };
}
