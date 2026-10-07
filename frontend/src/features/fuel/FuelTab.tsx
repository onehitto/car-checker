import { Fuel } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { api, expectNoContent } from "@/api/client";
import type { FuelRecord, FuelStatistics } from "@/api/types";
import { CHART, useChartDirection } from "@/components/charts/chartTheme";
import {
  Button,
  DetailList,
  EmptyState,
  ErrorState,
  LoadingState,
  LogList,
  LogRow,
  Pagination,
  Panel,
  RowMenu,
  Toolbar,
} from "@/components/ui";
import { useCurrentUser } from "@/features/auth/authContext";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { formatMonth } from "@/lib/format";
import { useFormat } from "@/lib/useFormat";
import { useSearchFilters } from "@/lib/useSearchFilters";

import { FuelFormDialog } from "./FuelFormDialog";
import { useFuelRecords, useFuelStatistics } from "./queries";

/** Fill-ups, consumption between full tanks and fuel spending. */
export function FuelTab() {
  const { t } = useTranslation();
  const format = useFormat();
  const user = useCurrentUser();
  const { vehicle, canEdit } = useVehicleContext();
  const { page, setPage } = useSearchFilters({});
  const records = useFuelRecords(vehicle.id, page);
  const statistics = useFuelStatistics(vehicle.id, user);
  const [editing, setEditing] = useState<FuelRecord | "new" | null>(null);
  const remove = useConfirmDelete(
    (record: FuelRecord) =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/fuel/{record_id}", {
          params: { path: { vehicle_id: vehicle.id, record_id: record.id } },
        }),
      ),
    { successMessage: t("fuel.deleted"), body: t("fuel.deleteBody") },
  );
  const currency = vehicle.currency;

  return (
    <>
      <Toolbar
        actions={
          canEdit && (
            <Button icon={<Fuel className="size-4" />} onClick={() => setEditing("new")}>
              {t("fuel.record")}
            </Button>
          )
        }
      />
      <div className="flex flex-col gap-6">
        {statistics.data && statistics.data.fill_up_count > 0 && (
          <FuelSummary statistics={statistics.data} />
        )}
        <Panel title={t("fuel.fillUps")} bodyClassName="py-1">
          {records.isPending ? (
            <LoadingState />
          ) : records.isError ? (
            <ErrorState error={records.error} onRetry={() => void records.refetch()} />
          ) : records.data.items.length === 0 ? (
            <EmptyState
              title={t("fuel.emptyTitle")}
              body={t("fuel.emptyBody")}
              action={
                canEdit && (
                  <Button icon={<Fuel className="size-4" />} onClick={() => setEditing("new")}>
                    {t("fuel.record")}
                  </Button>
                )
              }
            />
          ) : (
            <LogList>
              {records.data.items.map((record) => (
                <LogRow
                  key={record.id}
                  date={format.date(record.fill_date)}
                  mileage={format.distance(record.mileage)}
                  title={[
                    t("oil.liters", { value: format.number(Number(record.liters), 2) }),
                    record.price_per_liter &&
                      t("fuel.perLiter", {
                        price: format.money(record.price_per_liter, currency),
                      }),
                    record.gas_station,
                  ]
                    .filter(Boolean)
                    .join(", ")}
                  details={
                    record.consumption_l_100km != null && record.distance_since_previous != null
                      ? t("fuel.consumptionOver", {
                          consumption: format.consumption(record.consumption_l_100km),
                          distance: format.distance(record.distance_since_previous),
                        })
                      : record.full_tank
                        ? t("fuel.fullTank")
                        : t("fuel.partial")
                  }
                  amount={
                    record.total_price === null ? "" : format.money(record.total_price, currency)
                  }
                  actions={
                    canEdit && (
                      <RowMenu
                        label={t("common.moreActions")}
                        actions={[
                          { label: t("common.edit"), onSelect: () => setEditing(record) },
                          {
                            label: t("common.delete"),
                            danger: true,
                            onSelect: () => remove.ask(record),
                          },
                        ]}
                      />
                    )
                  }
                />
              ))}
            </LogList>
          )}
        </Panel>
      </div>
      {records.data && (
        <Pagination
          page={records.data.meta.page}
          totalPages={records.data.meta.total_pages}
          total={records.data.meta.total}
          onPageChange={setPage}
        />
      )}
      {editing && (
        <FuelFormDialog
          vehicle={vehicle}
          record={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {remove.dialog}
    </>
  );
}

function FuelSummary({ statistics }: { statistics: FuelStatistics }) {
  const { t } = useTranslation();
  const format = useFormat();
  const { rtl, yOrientation } = useChartDirection();
  const { currency } = statistics;
  const consumptionUnit = t(`units.consumption.${statistics.consumption_unit}`);
  const consumption = (value: number | null) =>
    value === null ? null : `${format.number(value, 1)} ${consumptionUnit}`;
  const monthly = statistics.monthly.map((month) => ({
    month: month.month,
    cost: Number(month.cost),
  }));

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <Panel title={t("fuel.summary")}>
        <DetailList
          items={[
            {
              label: t("overview.averageConsumption"),
              value: consumption(statistics.average_consumption),
            },
            { label: t("fuel.lastConsumption"), value: consumption(statistics.last_consumption) },
            {
              label: t("fuel.costPerDistance", { unit: statistics.distance_unit }),
              value:
                statistics.cost_per_distance_unit === null
                  ? null
                  : format.money(statistics.cost_per_distance_unit, currency),
            },
            {
              label: t("fuel.averagePrice"),
              value:
                statistics.average_price_per_liter === null
                  ? null
                  : format.money(statistics.average_price_per_liter, currency),
            },
            {
              label: t("fuel.totalLiters"),
              value: t("oil.liters", { value: format.number(Number(statistics.total_liters), 0) }),
            },
            { label: t("fuel.totalCost"), value: format.money(statistics.total_cost, currency) },
            { label: t("fuel.fillUpCount"), value: format.number(statistics.fill_up_count) },
            {
              label: t("fuel.distanceTracked"),
              value: `${format.number(statistics.distance_tracked)} ${statistics.distance_unit}`,
            },
          ]}
        />
      </Panel>
      {monthly.length > 0 && (
        <Panel title={t("fuel.monthlyCost")}>
          <figure>
            <figcaption className="sr-only">{t("fuel.monthlyCost")}</figcaption>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={monthly} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
                <CartesianGrid stroke={CHART.grid} vertical={false} />
                <XAxis
                  dataKey="month"
                  reversed={rtl}
                  tick={CHART.tick}
                  tickLine={false}
                  axisLine={{ stroke: CHART.grid }}
                  tickFormatter={(month: string) => formatMonth(format.locale, month)}
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
                  dataKey="cost"
                  fill={CHART.series}
                  radius={[3, 3, 0, 0]}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          </figure>
        </Panel>
      )}
    </div>
  );
}
