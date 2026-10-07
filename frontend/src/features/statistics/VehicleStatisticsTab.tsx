import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api, unwrap } from "@/api/client";
import type { VehicleStatistics } from "@/api/types";
import {
  DetailList,
  EmptyState,
  ErrorState,
  LoadingState,
  LogList,
  LogRow,
  Panel,
  Toolbar,
} from "@/components/ui";
import { vehicleKeys } from "@/features/vehicles/queries";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { useFormat } from "@/lib/useFormat";
import { useSearchFilters } from "@/lib/useSearchFilters";

import { MonthlyCostChart } from "./MonthlyCostChart";
import { PeriodSelect } from "./PeriodSelect";
import { ShareBars } from "./ShareBars";

export function VehicleStatisticsTab() {
  const { t } = useTranslation();
  const { vehicle } = useVehicleContext();
  const { values, update } = useSearchFilters({ year: "" });
  const year = values.year ? Number(values.year) : undefined;
  const statistics = useQuery({
    queryKey: vehicleKeys.part(vehicle.id, "statistics", year ?? "all"),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/vehicles/{vehicle_id}/statistics", {
          params: { path: { vehicle_id: vehicle.id }, query: { year } },
        }),
      ),
  });
  const sinceYear = Number(
    (vehicle.purchase_date ?? vehicle.created_at).slice(0, 4) || new Date().getFullYear(),
  );

  return (
    <>
      <Toolbar>
        <PeriodSelect
          value={values.year}
          onChange={(value) => update({ year: value })}
          sinceYear={sinceYear}
        />
      </Toolbar>
      {statistics.isPending ? (
        <LoadingState />
      ) : statistics.isError ? (
        <ErrorState error={statistics.error} onRetry={() => void statistics.refetch()} />
      ) : Number(statistics.data.total) === 0 ? (
        <Panel>
          <EmptyState title={t("statistics.emptyTitle")} body={t("statistics.emptyBody")} />
        </Panel>
      ) : (
        <Statistics data={statistics.data} />
      )}
    </>
  );
}

function Statistics({ data }: { data: VehicleStatistics }) {
  const { t } = useTranslation();
  const format = useFormat();
  const { currency } = data;
  return (
    <div className="flex flex-col gap-6">
      <Panel
        title={t("statistics.periodTitle", {
          from: format.date(data.period.date_from),
          to: format.date(data.period.date_to),
        })}
      >
        <DetailList
          className="sm:grid-cols-3"
          items={[
            { label: t("statistics.total"), value: format.money(data.total, currency) },
            {
              label: t("statistics.averageMonthly"),
              value: format.money(data.average_monthly_cost, currency),
            },
            {
              label: t("statistics.costPerDistance", { unit: format.unit }),
              value: format.perDistance(data.cost_per_km, currency),
            },
            {
              label: t("statistics.distanceDriven"),
              value: format.distance(data.distance_driven_km),
            },
            { label: t("statistics.services"), value: format.number(data.maintenance_count) },
            { label: t("statistics.repairs"), value: format.number(data.repair_count) },
          ]}
        />
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title={t("statistics.byMonth")}>
          <MonthlyCostChart
            months={data.by_month}
            currency={currency}
            label={t("statistics.byMonth")}
          />
        </Panel>
        <Panel title={t("statistics.byCategory")}>
          <ShareBars
            currency={currency}
            items={data.by_category.map((item) => ({
              key: item.category,
              label: t(`enums.expenseCategory.${item.category}`),
              total: item.total,
              share: item.share,
            }))}
          />
        </Panel>
      </div>

      {data.maintenance_frequency.length > 0 && (
        <Panel title={t("statistics.frequency")} bodyClassName="overflow-x-auto p-0">
          <table className="w-full min-w-[36rem] text-start">
            <thead className="border-b border-rule text-sm text-steel">
              <tr>
                <th className="px-4 py-2 text-start font-normal">{t("maintenance.fields.type")}</th>
                <th className="px-4 py-2 text-end font-normal">{t("statistics.times")}</th>
                <th className="px-4 py-2 text-end font-normal">{t("statistics.spent")}</th>
                <th className="px-4 py-2 text-end font-normal">{t("statistics.averageGap")}</th>
                <th className="px-4 py-2 text-end font-normal">{t("statistics.lastDone")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule numeric">
              {data.maintenance_frequency.map((row) => (
                <tr key={row.maintenance_type.id}>
                  <th className="px-4 py-2.5 text-start font-medium">
                    {row.maintenance_type.name}
                  </th>
                  <td className="px-4 py-2.5 text-end">{format.number(row.count)}</td>
                  <td className="px-4 py-2.5 text-end">{format.money(row.total_cost, currency)}</td>
                  <td className="px-4 py-2.5 text-end text-steel">
                    {[
                      row.average_interval_km !== null
                        ? format.distance(row.average_interval_km)
                        : null,
                      row.average_interval_days !== null
                        ? t("due.days", { count: row.average_interval_days })
                        : null,
                    ]
                      .filter(Boolean)
                      .join(", ") || "—"}
                  </td>
                  <td className="px-4 py-2.5 text-end">{format.date(row.last_service_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}

      <div className="grid gap-6 xl:grid-cols-2">
        {data.most_expensive_repairs.length > 0 && (
          <Panel title={t("statistics.expensiveRepairs")} bodyClassName="py-1">
            <LogList>
              {data.most_expensive_repairs.map((repair) => (
                <LogRow
                  key={repair.id}
                  date={format.date(repair.service_date)}
                  mileage={repair.mileage === null ? "" : format.distance(repair.mileage)}
                  title={repair.title}
                  amount={format.money(repair.cost, currency)}
                />
              ))}
            </LogList>
          </Panel>
        )}
        {data.by_year.length > 1 && (
          <Panel title={t("statistics.byYear")}>
            <ShareBars
              currency={currency}
              items={data.by_year.map((item) => ({
                key: String(item.year),
                label: String(item.year),
                total: item.total,
                share: Number(item.total) / Number(data.total),
              }))}
            />
          </Panel>
        )}
      </div>
    </div>
  );
}
