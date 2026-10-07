import { Plus } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent } from "@/api/client";
import type { OilChange } from "@/api/types";
import {
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

import { OilChangeFormDialog } from "./OilChangeFormDialog";
import { useOilChanges } from "./queries";

export function OilChangesTab() {
  const { t } = useTranslation();
  const format = useFormat();
  const { vehicle, canEdit } = useVehicleContext();
  const { page, setPage } = useSearchFilters({});
  const oilChanges = useOilChanges(vehicle.id, page);
  const [editing, setEditing] = useState<OilChange | "new" | null>(null);
  const remove = useConfirmDelete(
    (oilChange: OilChange) =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/oil-changes/{record_id}", {
          params: { path: { vehicle_id: vehicle.id, record_id: oilChange.id } },
        }),
      ),
    { successMessage: t("maintenance.deleted"), body: t("maintenance.deleteBody") },
  );

  const describe = (oilChange: OilChange) =>
    [
      oilChange.oil_viscosity,
      oilChange.oil_type ? t(`enums.oilType.${oilChange.oil_type}`) : null,
      oilChange.oil_quantity_liters
        ? t("oil.liters", { value: format.number(Number(oilChange.oil_quantity_liters), 1) })
        : null,
      oilChange.oil_brand,
    ]
      .filter(Boolean)
      .join(", ");

  return (
    <>
      <Toolbar
        actions={
          canEdit && (
            <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
              {t("oil.record")}
            </Button>
          )
        }
      />
      <Panel bodyClassName="py-1">
        {oilChanges.isPending ? (
          <LoadingState />
        ) : oilChanges.isError ? (
          <ErrorState error={oilChanges.error} onRetry={() => void oilChanges.refetch()} />
        ) : oilChanges.data.items.length === 0 ? (
          <EmptyState title={t("oil.emptyTitle")} body={t("oil.emptyBody")} />
        ) : (
          <LogList>
            {oilChanges.data.items.map((oilChange) => (
              <LogRow
                key={oilChange.id}
                date={format.date(oilChange.service_date)}
                mileage={oilChange.mileage === null ? "" : format.distance(oilChange.mileage)}
                title={describe(oilChange) || oilChange.title}
                details={[
                  oilChange.oil_filter_changed ? t("oil.withFilter") : t("oil.withoutFilter"),
                  oilChange.garage?.name,
                ]
                  .filter(Boolean)
                  .join(", ")}
                amount={
                  oilChange.cost === null ? "" : format.money(oilChange.cost, vehicle.currency)
                }
                actions={
                  canEdit && (
                    <RowMenu
                      label={t("common.moreActions")}
                      actions={[
                        { label: t("common.edit"), onSelect: () => setEditing(oilChange) },
                        {
                          label: t("common.delete"),
                          danger: true,
                          onSelect: () => remove.ask(oilChange),
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
      {oilChanges.data && (
        <Pagination
          page={oilChanges.data.meta.page}
          totalPages={oilChanges.data.meta.total_pages}
          total={oilChanges.data.meta.total}
          onPageChange={setPage}
        />
      )}
      {editing && (
        <OilChangeFormDialog
          vehicle={vehicle}
          oilChange={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {remove.dialog}
    </>
  );
}
