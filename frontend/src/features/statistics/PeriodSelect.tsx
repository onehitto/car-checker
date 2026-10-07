import { useTranslation } from "react-i18next";

import { FilterSelect } from "@/components/ui";

/** "All time" or a calendar year, from `sinceYear` to this year. */
export function PeriodSelect({
  value,
  onChange,
  sinceYear,
}: {
  value: string;
  onChange: (value: string) => void;
  sinceYear: number;
}) {
  const { t } = useTranslation();
  const thisYear = new Date().getFullYear();
  const years = Array.from(
    { length: Math.max(1, thisYear - Math.min(sinceYear, thisYear) + 1) },
    (_, index) => thisYear - index,
  );
  return (
    <FilterSelect
      label={t("statistics.period")}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="">{t("statistics.allTime")}</option>
      {years.map((year) => (
        <option key={year} value={String(year)}>
          {year}
        </option>
      ))}
    </FilterSelect>
  );
}
