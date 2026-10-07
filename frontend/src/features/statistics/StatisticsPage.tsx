import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api, unwrap } from "@/api/client";
import type { GlobalStatistics } from "@/api/types";
import {
  EmptyState,
  ErrorState,
  FilterSelect,
  LoadingState,
  PageHeader,
  Panel,
  Toolbar,
} from "@/components/ui";
import { useVehicleList } from "@/features/vehicles/queries";
import { useFormat } from "@/lib/useFormat";
import { useSearchFilters } from "@/lib/useSearchFilters";

import { MonthlyCostChart } from "./MonthlyCostChart";
import { PeriodSelect } from "./PeriodSelect";
import { ShareBars } from "./ShareBars";

type CurrencyStatistics = GlobalStatistics["currencies"][number];

/** /statistics — spending across the user's vehicles, one block per currency. */
export function StatisticsPage() {
  const { t } = useTranslation();
  const { values, update } = useSearchFilters({ year: "", vehicle_id: "" });
  const vehicles = useVehicleList({ limit: 100, sort: "created_at" });
  const year = values.year ? Number(values.year) : undefined;
  const vehicleId = values.vehicle_id || undefined;
  const statistics = useQuery({
    queryKey: ["statistics", { year, vehicleId }],
    queryFn: () =>
      unwrap(api.GET("/api/v1/statistics", { params: { query: { year, vehicle_id: vehicleId } } })),
  });
  const sinceYear = Math.min(
    new Date().getFullYear(),
    ...(vehicles.data?.items ?? []).map((vehicle) =>
      Number((vehicle.purchase_date ?? vehicle.created_at).slice(0, 4)),
    ),
  );

  return (
    <>
      <PageHeader title={t("statistics.title")} description={t("statistics.description")} />
      <Toolbar>
        <PeriodSelect
          value={values.year}
          onChange={(value) => update({ year: value })}
          sinceYear={sinceYear}
        />
        <FilterSelect
          label={t("statistics.vehicle")}
          value={values.vehicle_id}
          onChange={(event) => update({ vehicle_id: event.target.value })}
        >
          <option value="">{t("statistics.allVehicles")}</option>
          {vehicles.data?.items.map((vehicle) => (
            <option key={vehicle.id} value={vehicle.id}>
              {vehicle.display_name}
            </option>
          ))}
        </FilterSelect>
      </Toolbar>
      {statistics.isPending ? (
        <LoadingState />
      ) : statistics.isError ? (
        <ErrorState error={statistics.error} onRetry={() => void statistics.refetch()} />
      ) : statistics.data.currencies.length === 0 ? (
        <Panel>
          <EmptyState title={t("statistics.emptyTitle")} body={t("statistics.emptyBody")} />
        </Panel>
      ) : (
        <div className="flex flex-col gap-10">
          {statistics.data.currencies.map((block) => (
            <CurrencyBlock key={block.currency} block={block} showVehicles={!vehicleId} />
          ))}
        </div>
      )}
    </>
  );
}

function CurrencyBlock({
  block,
  showVehicles,
}: {
  block: CurrencyStatistics;
  showVehicles: boolean;
}) {
  const { t } = useTranslation();
  const format = useFormat();
  const { currency } = block;
  const total = Number(block.total);
  return (
    <section className="flex flex-col gap-6" aria-label={currency}>
      <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-rule pb-2">
        <h2 className="text-2xl">{t("statistics.currencyTotal", { currency })}</h2>
        <p className="font-display text-3xl font-semibold numeric">
          {format.money(block.total, currency)}
        </p>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title={t("statistics.byMonth")}>
          <MonthlyCostChart
            months={block.by_month}
            currency={currency}
            label={t("statistics.byMonth")}
          />
        </Panel>
        <Panel title={t("statistics.byCategory")}>
          <ShareBars
            currency={currency}
            items={block.by_category.map((item) => ({
              key: item.category,
              label: t(`enums.expenseCategory.${item.category}`),
              total: item.total,
              share: item.share,
            }))}
          />
        </Panel>
      </div>
      {showVehicles && block.by_vehicle.length > 1 && (
        <Panel title={t("statistics.byVehicle")}>
          <ShareBars
            currency={currency}
            items={block.by_vehicle.map((item) => ({
              key: item.vehicle_id,
              label: item.display_name,
              total: item.total,
              share: total > 0 ? Number(item.total) / total : 0,
            }))}
          />
        </Panel>
      )}
    </section>
  );
}
