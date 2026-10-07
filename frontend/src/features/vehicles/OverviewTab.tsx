import { useTranslation } from "react-i18next";

import type { VehicleDashboard } from "@/api/types";
import {
  DetailList,
  EmptyState,
  ErrorState,
  ItemRow,
  LoadingState,
  LogList,
  LogRow,
  Panel,
  PanelLink,
  StatusBadge,
} from "@/components/ui";
import { AlertRow } from "@/features/alerts/AlertRow";
import { useDueText } from "@/features/maintenance/useDueText";
import { useFormat } from "@/lib/useFormat";

import { HealthPanel } from "./HealthPanel";
import { useVehicleDashboard } from "./queries";
import { useVehicleContext } from "./vehicleContext";

export function OverviewTab() {
  const { vehicle } = useVehicleContext();
  const dashboard = useVehicleDashboard(vehicle.id);
  if (dashboard.isPending) return <LoadingState />;
  if (dashboard.isError)
    return <ErrorState error={dashboard.error} onRetry={() => void dashboard.refetch()} />;
  return <Overview data={dashboard.data} />;
}

function Overview({ data }: { data: VehicleDashboard }) {
  const { t } = useTranslation();
  const format = useFormat();
  const dueText = useDueText();
  const { vehicle } = data;
  const base = `/vehicles/${vehicle.id}`;
  const attention = [...data.maintenance.overdue, ...data.maintenance.upcoming];
  const documents = [...data.documents.expired, ...data.documents.expiring];
  const currency = data.costs.currency;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="flex min-w-0 flex-col gap-6">
        <Panel
          title={t("overview.attention")}
          actions={
            <PanelLink to={`${base}/maintenance/schedules`}>{t("overview.schedules")}</PanelLink>
          }
          bodyClassName="py-1"
        >
          {attention.length === 0 && data.worn_parts.length === 0 ? (
            <p className="py-3 text-steel">{t("overview.nothingDue")}</p>
          ) : (
            <ul className="divide-y divide-rule">
              {attention.map((schedule) => (
                <ItemRow
                  key={schedule.id}
                  title={schedule.maintenance_type.name}
                  details={dueText(schedule)}
                  aside={<StatusBadge status={schedule.status} />}
                />
              ))}
              {data.worn_parts.map((part) => (
                <ItemRow
                  key={part.id}
                  title={part.part_name}
                  details={part.lifetime ? dueText(part.lifetime) : undefined}
                  aside={<StatusBadge status={part.lifetime?.status ?? "due"} />}
                />
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          title={t("overview.serviceHistory")}
          actions={<PanelLink to={`${base}/maintenance`}>{t("overview.seeAll")}</PanelLink>}
          bodyClassName="py-1"
        >
          {data.recent_maintenance.length === 0 ? (
            <EmptyState title={t("overview.noService")} body={t("overview.noServiceBody")} />
          ) : (
            <LogList>
              {data.recent_maintenance.map((record) => (
                <LogRow
                  key={record.id}
                  date={format.date(record.service_date)}
                  mileage={record.mileage === null ? "" : format.distance(record.mileage)}
                  title={record.title}
                  details={record.garage?.name}
                  amount={record.cost === null ? "" : format.money(record.cost, currency)}
                />
              ))}
            </LogList>
          )}
        </Panel>

        <Panel
          title={t("overview.recentExpenses")}
          actions={<PanelLink to={`${base}/expenses`}>{t("overview.seeAll")}</PanelLink>}
          bodyClassName="py-1"
        >
          {data.recent_expenses.length === 0 ? (
            <p className="py-3 text-steel">{t("overview.noExpenses")}</p>
          ) : (
            <LogList>
              {data.recent_expenses.map((expense) => (
                <LogRow
                  key={expense.id}
                  date={format.date(expense.expense_date)}
                  mileage={expense.mileage === null ? "" : format.distance(expense.mileage)}
                  title={expense.title}
                  details={t(`enums.expenseCategory.${expense.category}`)}
                  amount={format.money(expense.amount, expense.currency)}
                />
              ))}
            </LogList>
          )}
        </Panel>
      </div>

      <aside className="flex flex-col gap-6">
        <HealthPanel health={data.health} />

        <Panel
          title={t("overview.documents")}
          actions={<PanelLink to={`${base}/documents`}>{t("overview.seeAll")}</PanelLink>}
          bodyClassName="py-1"
        >
          {documents.length === 0 ? (
            <p className="py-3 text-steel">{t("overview.documentsOk")}</p>
          ) : (
            <ul className="divide-y divide-rule">
              {documents.map((document) => (
                <ItemRow
                  key={document.id}
                  title={document.title}
                  details={
                    document.expiration_date &&
                    t(
                      document.status === "expired" ? "documents.expiredOn" : "documents.expiresOn",
                      {
                        date: format.date(document.expiration_date),
                      },
                    )
                  }
                  aside={<StatusBadge status={document.status ?? "valid"} />}
                />
              ))}
            </ul>
          )}
        </Panel>

        <Panel title={t("overview.costs")}>
          <DetailList
            className="sm:grid-cols-2 lg:grid-cols-2"
            items={[
              {
                label: t("overview.thisMonth"),
                value: format.money(data.costs.this_month, currency),
              },
              {
                label: t("overview.thisYear"),
                value: format.money(data.costs.this_year, currency),
              },
              { label: t("overview.totalSpent"), value: format.money(data.costs.total, currency) },
              {
                label: t("overview.maintenanceSpent"),
                value: format.money(data.costs.total_maintenance_cost, currency),
              },
              {
                label: t("overview.averageConsumption"),
                value: format.consumption(data.fuel.average_consumption_l_100km),
              },
              {
                label: t("overview.fuelCost"),
                value: format.perDistance(data.fuel.cost_per_km, currency),
              },
            ]}
          />
        </Panel>

        {data.alerts.latest.length > 0 && (
          <Panel
            title={t("overview.alerts")}
            actions={
              <PanelLink to={`/alerts?vehicle_id=${vehicle.id}`}>{t("overview.seeAll")}</PanelLink>
            }
            bodyClassName="py-1"
          >
            <ul className="divide-y divide-rule">
              {data.alerts.latest.map((alert) => (
                <AlertRow key={alert.id} alert={alert} compact />
              ))}
            </ul>
          </Panel>
        )}
      </aside>
    </div>
  );
}
