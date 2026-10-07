import { useMutation } from "@tanstack/react-query";
import { CheckCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { api, unwrap } from "@/api/client";
import { ALERT_PRIORITIES } from "@/api/enums";
import type { Alert } from "@/api/types";
import {
  Button,
  EmptyState,
  errorMessage,
  ErrorState,
  FilterSelect,
  LoadingState,
  PageHeader,
  Pagination,
  Panel,
  RowMenu,
  Toolbar,
  useToast,
} from "@/components/ui";
import { useVehicleList } from "@/features/vehicles/queries";
import { useSearchFilters } from "@/lib/useSearchFilters";

import { AlertRow } from "./AlertRow";
import { type AlertFilters, useAlertSummary, useAlerts } from "./queries";

/** Which statuses each "show" option lists. */
const SHOW: Record<string, Alert["status"][] | undefined> = {
  open: ["active", "read"],
  active: ["active"],
  dismissed: ["dismissed"],
  resolved: ["resolved"],
  all: undefined,
};

/** Where to act on an alert, from what raised it. */
function alertTarget(alert: Alert): string | null {
  if (!alert.vehicle_id) return null;
  const base = `/vehicles/${alert.vehicle_id}`;
  switch (alert.source_type) {
    case "maintenance_schedule":
      return `${base}/maintenance/schedules`;
    case "vehicle_document":
      return `${base}/documents`;
    case "part_replacement":
      return `${base}/maintenance/parts`;
    case "reminder":
      return `${base}/reminders`;
    case "vehicle":
      return `${base}/mileage`;
    default:
      return base;
  }
}

export function AlertsPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const { values, page, update, setPage } = useSearchFilters({
    show: "open",
    priority: "",
    vehicle_id: "",
  });
  const vehicles = useVehicleList({ limit: 100, sort: "created_at" });
  const names = new Map(vehicles.data?.items.map((vehicle) => [vehicle.id, vehicle.display_name]));
  const summary = useAlertSummary();
  const alerts = useAlerts({
    page,
    status: SHOW[values.show] ?? SHOW.open,
    priority: values.priority ? [values.priority as Alert["priority"]] : undefined,
    vehicle_id: values.vehicle_id || undefined,
  } satisfies AlertFilters);

  const setStatus = useMutation({
    mutationFn: ({ alert, status }: { alert: Alert; status: Alert["status"] }) =>
      unwrap(
        api.PATCH("/api/v1/alerts/{alert_id}", {
          params: { path: { alert_id: alert.id } },
          body: { status },
        }),
      ),
    onError: (error) => toast.error(errorMessage(error, t)),
  });
  const readAll = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/api/v1/alerts/read-all", {
          params: { query: { vehicle_id: values.vehicle_id || undefined } },
        }),
      ),
    onSuccess: () => toast.success(t("alerts.allRead")),
    onError: (error) => toast.error(errorMessage(error, t)),
  });

  const open = (alert: Alert) => {
    if (alert.status === "active") setStatus.mutate({ alert, status: "read" });
    const target = alertTarget(alert);
    if (target) void navigate(target);
  };

  return (
    <>
      <PageHeader
        title={t("alerts.title")}
        description={t("alerts.description")}
        actions={
          (summary.data?.unread ?? 0) > 0 && (
            <Button
              variant="secondary"
              icon={<CheckCheck className="size-4" />}
              loading={readAll.isPending}
              onClick={() => readAll.mutate()}
            >
              {t("alerts.markAllRead")}
            </Button>
          )
        }
      />
      <Toolbar>
        <FilterSelect
          label={t("alerts.show")}
          value={values.show}
          onChange={(event) => update({ show: event.target.value })}
        >
          <option value="open">{t("alerts.filters.open")}</option>
          <option value="active">{t("alerts.filters.unread")}</option>
          <option value="dismissed">{t("alerts.filters.dismissed")}</option>
          <option value="resolved">{t("alerts.filters.resolved")}</option>
          <option value="all">{t("alerts.filters.all")}</option>
        </FilterSelect>
        <FilterSelect
          label={t("alerts.priority")}
          value={values.priority}
          onChange={(event) => update({ priority: event.target.value })}
        >
          <option value="">{t("alerts.anyPriority")}</option>
          {ALERT_PRIORITIES.map((priority) => (
            <option key={priority} value={priority}>
              {t(`status.${priority}`)}
            </option>
          ))}
        </FilterSelect>
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
      <Panel bodyClassName="py-1">
        {alerts.isPending ? (
          <LoadingState />
        ) : alerts.isError ? (
          <ErrorState error={alerts.error} onRetry={() => void alerts.refetch()} />
        ) : alerts.data.items.length === 0 ? (
          <EmptyState title={t("alerts.emptyTitle")} body={t("alerts.emptyBody")} />
        ) : (
          <ul className="divide-y divide-rule">
            {alerts.data.items.map((alert) => (
              <AlertRow
                key={alert.id}
                alert={alert}
                vehicleName={alert.vehicle_id ? names.get(alert.vehicle_id) : undefined}
                onOpen={alertTarget(alert) ? () => open(alert) : undefined}
                actions={
                  <div className="w-8 shrink-0">
                    <RowMenu
                      label={t("common.moreActions")}
                      actions={[
                        alert.status === "active" && {
                          label: t("alerts.markRead"),
                          onSelect: () => setStatus.mutate({ alert, status: "read" }),
                        },
                        alert.status === "read" && {
                          label: t("alerts.markUnread"),
                          onSelect: () => setStatus.mutate({ alert, status: "active" }),
                        },
                        (alert.status === "active" || alert.status === "read") && {
                          label: t("alerts.dismiss"),
                          onSelect: () => setStatus.mutate({ alert, status: "dismissed" }),
                        },
                        alert.status === "dismissed" && {
                          label: t("alerts.restore"),
                          onSelect: () => setStatus.mutate({ alert, status: "read" }),
                        },
                      ]}
                    />
                  </div>
                }
              />
            ))}
          </ul>
        )}
      </Panel>
      {alerts.data && (
        <Pagination
          page={alerts.data.meta.page}
          totalPages={alerts.data.meta.total_pages}
          total={alerts.data.meta.total}
          onPageChange={setPage}
        />
      )}
    </>
  );
}
