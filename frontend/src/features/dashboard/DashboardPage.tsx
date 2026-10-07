import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { api, unwrap } from "@/api/client";
import type { GlobalDashboard } from "@/api/types";
import {
  Badge,
  ButtonLink,
  EmptyState,
  ErrorState,
  ItemRow,
  LoadingState,
  Odometer,
  PageHeader,
  Panel,
  PanelLink,
  Plate,
  StatusBadge,
  type Tone,
} from "@/components/ui";
import { AlertRow } from "@/features/alerts/AlertRow";
import { useCurrentUser } from "@/features/auth/authContext";
import { useDueText } from "@/features/maintenance/useDueText";
import { cn } from "@/lib/cn";
import { useFormat } from "@/lib/useFormat";

const HEALTH_TONES: Record<string, Tone> = { good: "ok", attention: "soon", critical: "overdue" };

export function DashboardPage() {
  const { t } = useTranslation();
  const user = useCurrentUser();
  const dashboard = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => unwrap(api.GET("/api/v1/dashboard")),
  });

  return (
    <>
      <PageHeader title={t("dashboard.greeting", { name: user.first_name })} />
      {dashboard.isPending ? (
        <LoadingState />
      ) : dashboard.isError ? (
        <ErrorState error={dashboard.error} onRetry={() => void dashboard.refetch()} />
      ) : dashboard.data.vehicles.length === 0 ? (
        <Panel>
          <EmptyState
            title={t("vehicles.emptyTitle")}
            body={t("dashboard.emptyBody")}
            action={
              <ButtonLink to="/vehicles/new" variant="primary" icon={<Plus className="size-4" />}>
                {t("nav.addVehicle")}
              </ButtonLink>
            }
          />
        </Panel>
      ) : (
        <Dashboard data={dashboard.data} />
      )}
    </>
  );
}

function Dashboard({ data }: { data: GlobalDashboard }) {
  const { t } = useTranslation();
  const format = useFormat();
  const dueText = useDueText();
  const names = new Map(data.vehicles.map(({ vehicle }) => [vehicle.id, vehicle.display_name]));

  return (
    <div className="flex flex-col gap-6">
      <Telltales totals={data.totals} />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex min-w-0 flex-col gap-6">
          <Panel
            title={t("dashboard.vehicles")}
            actions={<PanelLink to="/vehicles">{t("overview.seeAll")}</PanelLink>}
            bodyClassName="py-1"
          >
            <ul className="divide-y divide-rule">
              {data.vehicles.map(({ vehicle, health, next_maintenance, open_alerts }) => (
                <li key={vehicle.id} className="flex flex-wrap items-center gap-x-5 gap-y-2 py-3">
                  <div className="min-w-0 flex-1 basis-56">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      <Link
                        to={`/vehicles/${vehicle.id}`}
                        className="font-display text-xl font-semibold hover:text-petrol"
                      >
                        {vehicle.display_name}
                      </Link>
                      {vehicle.license_plate && <Plate value={vehicle.license_plate} />}
                    </div>
                    <p className="text-sm text-steel">
                      {next_maintenance
                        ? t("dashboard.next", {
                            name: next_maintenance.maintenance_type.name,
                            due: dueText(next_maintenance),
                          })
                        : t("dashboard.nothingPlanned")}
                    </p>
                    {open_alerts > 0 && (
                      <Link
                        to={`/alerts?vehicle_id=${vehicle.id}`}
                        className="text-sm text-petrol hover:underline"
                      >
                        {t("dashboard.openAlerts", { count: open_alerts })}
                      </Link>
                    )}
                  </div>
                  <Odometer
                    size="sm"
                    value={format.toUnit(vehicle.current_mileage)}
                    unit={format.unit}
                    label={format.distance(vehicle.current_mileage)}
                  />
                  <Badge tone={HEALTH_TONES[health.level] ?? "neutral"}>
                    {t(`health.level.${health.level}`)}
                  </Badge>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title={t("dashboard.comingUp")} bodyClassName="py-1">
            {data.upcoming_maintenance.length === 0 ? (
              <p className="py-3 text-steel">{t("overview.nothingDue")}</p>
            ) : (
              <ul className="divide-y divide-rule">
                {data.upcoming_maintenance.map((item) => (
                  <ItemRow
                    key={item.id}
                    title={
                      <Link
                        to={`/vehicles/${item.vehicle_id}/maintenance/schedules`}
                        className="hover:text-petrol"
                      >
                        {item.maintenance_type.name}
                      </Link>
                    }
                    details={`${item.vehicle_name}: ${dueText(item)}`}
                    aside={<StatusBadge status={item.status} />}
                  />
                ))}
              </ul>
            )}
          </Panel>
        </div>

        <aside className="flex flex-col gap-6">
          <Panel title={t("dashboard.documents")} bodyClassName="py-1">
            {data.expiring_documents.length === 0 ? (
              <p className="py-3 text-steel">{t("overview.documentsOk")}</p>
            ) : (
              <ul className="divide-y divide-rule">
                {data.expiring_documents.map((document) => (
                  <ItemRow
                    key={document.id}
                    title={
                      <Link
                        to={`/vehicles/${document.vehicle_id}/documents`}
                        className="hover:text-petrol"
                      >
                        {document.title}
                      </Link>
                    }
                    details={
                      document.expiration_date
                        ? `${document.vehicle_name}: ${t(
                            document.status === "expired"
                              ? "documents.expiredOn"
                              : "documents.expiresOn",
                            { date: format.date(document.expiration_date) },
                          )}`
                        : document.vehicle_name
                    }
                    aside={<StatusBadge status={document.status ?? "valid"} />}
                  />
                ))}
              </ul>
            )}
          </Panel>

          <Panel title={t("dashboard.spending")}>
            {data.costs.length === 0 ? (
              <p className="text-steel">{t("overview.noExpenses")}</p>
            ) : (
              <table className="w-full text-start">
                <thead>
                  <tr className="text-sm text-steel">
                    <th className="pb-1 text-start font-normal">
                      <span className="sr-only">{t("auth.currency")}</span>
                    </th>
                    <th className="pb-1 text-end font-normal">{t("overview.thisMonth")}</th>
                    <th className="pb-1 text-end font-normal">{t("overview.thisYear")}</th>
                  </tr>
                </thead>
                <tbody className="numeric">
                  {data.costs.map((row) => (
                    <tr key={row.currency}>
                      <th className="py-1 text-start text-sm font-medium text-steel">
                        {row.currency}
                      </th>
                      <td className="py-1 text-end">
                        {format.money(row.this_month, row.currency)}
                      </td>
                      <td className="py-1 text-end font-medium">
                        {format.money(row.this_year, row.currency)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Panel>

          {data.alerts.latest.length > 0 && (
            <Panel
              title={t("overview.alerts")}
              actions={<PanelLink to="/alerts">{t("overview.seeAll")}</PanelLink>}
              bodyClassName="py-1"
            >
              <ul className="divide-y divide-rule">
                {data.alerts.latest.map((alert) => (
                  <AlertRow
                    key={alert.id}
                    alert={alert}
                    compact
                    vehicleName={alert.vehicle_id ? names.get(alert.vehicle_id) : undefined}
                  />
                ))}
              </ul>
            </Panel>
          )}
        </aside>
      </div>
    </div>
  );
}

const LAMP_STYLES: Record<Tone, string> = {
  ok: "bg-ok text-white",
  upcoming: "bg-upcoming text-white",
  soon: "bg-soon text-white",
  due: "bg-due text-white",
  overdue: "bg-overdue text-white",
  neutral: "bg-steel text-white",
};

/** Warning lamps of the instrument cluster: lit when something needs doing. */
function Telltales({ totals }: { totals: GlobalDashboard["totals"] }) {
  const { t } = useTranslation();
  const lamps: { count: number; label: string; tone: Tone; to?: string }[] = [
    {
      count: totals.overdue_maintenance,
      label: t("dashboard.lamps.overdue", { count: totals.overdue_maintenance }),
      tone: "overdue",
    },
    {
      count: totals.due_maintenance,
      label: t("dashboard.lamps.due", { count: totals.due_maintenance }),
      tone: "due",
    },
    {
      count: totals.expired_documents,
      label: t("dashboard.lamps.expired", { count: totals.expired_documents }),
      tone: "overdue",
    },
    {
      count: totals.expiring_documents,
      label: t("dashboard.lamps.expiring", { count: totals.expiring_documents }),
      tone: "soon",
    },
    {
      count: totals.open_alerts,
      label: t("dashboard.lamps.alerts", { count: totals.open_alerts }),
      tone: "upcoming",
      to: "/alerts",
    },
  ];
  return (
    <ul
      aria-label={t("dashboard.lampsLabel")}
      className="flex flex-wrap gap-px overflow-hidden rounded-panel border border-rule bg-rule"
    >
      {lamps.map((lamp) => (
        <li key={lamp.label} className="min-w-40 flex-1 bg-sheet">
          {lamp.to ? (
            <Link to={lamp.to} className="flex h-full items-center gap-3 px-4 py-3 hover:bg-paper">
              <Lamp {...lamp} />
            </Link>
          ) : (
            <div className="flex h-full items-center gap-3 px-4 py-3">
              <Lamp {...lamp} />
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}

function Lamp({ count, label, tone }: { count: number; label: string; tone: Tone }) {
  return (
    <>
      <span
        className={cn(
          "grid size-9 shrink-0 place-items-center rounded-full font-display text-lg font-semibold numeric",
          count > 0 ? LAMP_STYLES[tone] : "bg-paper text-steel",
        )}
      >
        {count}
      </span>
      <span className="text-sm leading-tight">{label}</span>
    </>
  );
}
