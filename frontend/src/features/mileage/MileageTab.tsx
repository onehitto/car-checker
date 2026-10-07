import { Gauge } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent } from "@/api/client";
import type { MileageEntry } from "@/api/types";
import {
  Badge,
  Button,
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
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { useFormat } from "@/lib/useFormat";
import { useSearchFilters } from "@/lib/useSearchFilters";

import { MileageChart } from "./MileageChart";
import { MileageDialog } from "./MileageDialog";
import { useMileageEntries } from "./queries";

/** Odometer readings: typed by hand or taken from services, fill-ups, parts and tires. */
export function MileageTab() {
  const { t } = useTranslation();
  const format = useFormat();
  const { vehicle, canEdit } = useVehicleContext();
  const { page, setPage } = useSearchFilters({});
  const entries = useMileageEntries(vehicle.id, page);
  const history = useMileageEntries(vehicle.id, 1, 100);
  const [adding, setAdding] = useState(false);
  const remove = useConfirmDelete(
    (entry: MileageEntry) =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/mileage/{entry_id}", {
          params: { path: { vehicle_id: vehicle.id, entry_id: entry.id } },
        }),
      ),
    { successMessage: t("mileage.deleted"), body: t("mileage.deleteBody") },
  );

  return (
    <>
      <Toolbar
        actions={
          canEdit && (
            <Button icon={<Gauge className="size-4" />} onClick={() => setAdding(true)}>
              {t("mileage.update")}
            </Button>
          )
        }
      >
        <p className="max-w-prose text-sm text-steel">{t("mileage.intro")}</p>
      </Toolbar>
      <div className="flex flex-col gap-6">
        {history.data && history.data.items.length > 1 && (
          <Panel title={t("mileage.chartTitle")}>
            <MileageChart entries={history.data.items} />
          </Panel>
        )}
        <Panel title={t("mileage.readings")} bodyClassName="py-1">
          {entries.isPending ? (
            <LoadingState />
          ) : entries.isError ? (
            <ErrorState error={entries.error} onRetry={() => void entries.refetch()} />
          ) : entries.data.items.length === 0 ? (
            <EmptyState title={t("mileage.emptyTitle")} body={t("mileage.emptyBody")} />
          ) : (
            <LogList>
              {entries.data.items.map((entry) => (
                <LogRow
                  key={entry.id}
                  date={format.date(entry.recorded_on)}
                  mileage={format.distance(entry.mileage)}
                  title={
                    <Badge tone={entry.source === "manual" ? "upcoming" : "neutral"}>
                      {t(`enums.mileageSource.${entry.source}`)}
                    </Badge>
                  }
                  details={entry.notes}
                  actions={
                    canEdit && (
                      <RowMenu
                        label={t("common.moreActions")}
                        actions={[
                          {
                            label: t("common.delete"),
                            danger: true,
                            onSelect: () => remove.ask(entry),
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
      {entries.data && (
        <Pagination
          page={entries.data.meta.page}
          totalPages={entries.data.meta.total_pages}
          total={entries.data.meta.total}
          onPageChange={setPage}
        />
      )}
      {adding && <MileageDialog vehicle={vehicle} onClose={() => setAdding(false)} />}
      {remove.dialog}
    </>
  );
}
