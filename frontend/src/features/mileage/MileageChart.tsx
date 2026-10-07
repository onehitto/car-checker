import { useTranslation } from "react-i18next";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { MileageEntry } from "@/api/types";
import { CHART, useChartDirection } from "@/components/charts/chartTheme";
import { useFormat } from "@/lib/useFormat";

/** Odometer readings over time. */
export function MileageChart({ entries }: { entries: MileageEntry[] }) {
  const { t } = useTranslation();
  const format = useFormat();
  const { rtl, yOrientation } = useChartDirection();
  const data = [...entries]
    .sort((a, b) => a.recorded_on.localeCompare(b.recorded_on) || a.mileage - b.mileage)
    .map((entry) => ({
      date: Date.parse(entry.recorded_on),
      mileage: format.toUnit(entry.mileage),
    }));
  if (data.length < 2) return null;
  return (
    <figure dir="ltr">
      <figcaption className="sr-only">{t("mileage.chartLabel")}</figcaption>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis
            dataKey="date"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            reversed={rtl}
            tick={CHART.tick}
            tickLine={false}
            axisLine={{ stroke: CHART.grid }}
            tickFormatter={(value: number) =>
              new Intl.DateTimeFormat(format.locale, { month: "short", year: "numeric" }).format(
                value,
              )
            }
            minTickGap={32}
            tickMargin={8}
          />
          <YAxis
            orientation={yOrientation}
            tick={CHART.tick}
            tickLine={false}
            axisLine={false}
            width={72}
            domain={["dataMin", "auto"]}
            tickFormatter={(value: number) => format.number(value)}
          />
          <Tooltip
            formatter={(value) => [`${format.number(Number(value))} ${format.unitLabel}`, ""]}
            labelFormatter={(value) => format.date(new Date(Number(value)).toISOString())}
            separator=""
          />
          <Area
            type="monotone"
            dataKey="mileage"
            stroke={CHART.series}
            strokeWidth={2}
            fill={CHART.seriesSoft}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </figure>
  );
}
