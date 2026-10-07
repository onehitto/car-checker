import { useTranslation } from "react-i18next";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { CHART, useChartDirection } from "@/components/charts/chartTheme";
import { formatMonth } from "@/lib/format";
import { useFormat } from "@/lib/useFormat";

import { fillMonths } from "./months";

export function MonthlyCostChart({
  months,
  currency,
  label,
}: {
  months: { month: string; total: string }[];
  currency: string;
  label: string;
}) {
  const { t } = useTranslation();
  const format = useFormat();
  const { rtl, yOrientation } = useChartDirection();
  const data = fillMonths(months);
  if (data.length === 0) return <p className="text-steel">{t("statistics.noData")}</p>;
  const long = data.length > 12;
  return (
    <figure>
      <figcaption className="sr-only">{label}</figcaption>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis
            dataKey="month"
            reversed={rtl}
            tick={CHART.tick}
            tickLine={false}
            tickMargin={8}
            axisLine={{ stroke: CHART.grid }}
            minTickGap={16}
            tickFormatter={(month: string) =>
              long
                ? new Intl.DateTimeFormat(format.locale, {
                    month: "short",
                    year: "2-digit",
                    timeZone: "UTC",
                  }).format(new Date(`${month}-01T00:00:00Z`))
                : formatMonth(format.locale, month)
            }
          />
          <YAxis
            orientation={yOrientation}
            tick={CHART.tick}
            tickLine={false}
            axisLine={false}
            width={64}
            tickFormatter={(value: number) => format.number(value)}
          />
          <Tooltip
            cursor={{ fill: CHART.seriesSoft }}
            formatter={(value) => [format.money(Number(value), currency), ""]}
            labelFormatter={(month) => formatMonth(format.locale, String(month), true)}
            separator=""
          />
          <Bar
            dataKey="total"
            fill={CHART.series}
            radius={[3, 3, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </figure>
  );
}
