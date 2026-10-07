import { Plus } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent } from "@/api/client";
import { MAINTENANCE_KINDS } from "@/api/enums";
import type { MaintenanceRecord } from "@/api/types";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  FilterSelect,
  LoadingState,
  LogList,
  LogRow,
  Pagination,
  Panel,
  RowMenu,
  Toolbar,
} from "@/components/ui";
import { AttachmentsDialog } from "@/features/attachments/AttachmentsDialog";
import { MaintenanceTypeSelect } from "@/features/catalog/selects";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { useFormat } from "@/lib/useFormat";
import { useSearchFilters } from "@/lib/useSearchFilters";

import { type RecordFilters, useMaintenanceRecords } from "./queries";
import { RecordDetailsDialog } from "./RecordDetailsDialog";
import { RecordFormDialog } from "./RecordFormDialog";

/** Service history: maintenance and repairs, newest first. */
export function RecordsTab() {
  const { t } = useTranslation();
  const format = useFormat();
  const { vehicle, canEdit } = useVehicleContext();
  const { values, page, update, setPage } = useSearchFilters({ kind: "", type: "" });
  const records = useMaintenanceRecords(vehicle.id, {
    page,
    kind: (values.kind || undefined) as RecordFilters["kind"],
    maintenance_type_id: values.type || undefined,
  });
  const [editing, setEditing] = useState<MaintenanceRecord | "new" | null>(null);
  const [viewing, setViewing] = useState<MaintenanceRecord | null>(null);
  const [files, setFiles] = useState<MaintenanceRecord | null>(null);
  const remove = useConfirmDelete(
    (record: MaintenanceRecord) =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/maintenance/{record_id}", {
          params: { path: { vehicle_id: vehicle.id, record_id: record.id } },
        }),
      ),
    { successMessage: t("maintenance.deleted"), body: t("maintenance.deleteBody") },
  );
  const filtered = values.kind !== "" || values.type !== "";

  return (
    <>
      <Toolbar
        actions={
          canEdit && (
            <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
              {t("maintenance.record")}
            </Button>
          )
        }
      >
        <FilterSelect
          label={t("maintenance.fields.kind")}
          value={values.kind}
          onChange={(event) => update({ kind: event.target.value })}
        >
          <option value="">{t("maintenance.allKinds")}</option>
          {MAINTENANCE_KINDS.map((kind) => (
            <option key={kind} value={kind}>
              {t(`enums.maintenanceKind.${kind}`)}
            </option>
          ))}
        </FilterSelect>
        <label>
          <span className="sr-only">{t("maintenance.fields.type")}</span>
          <MaintenanceTypeSelect
            className="w-auto min-w-48"
            placeholder={t("maintenance.allTypes")}
            value={values.type}
            onChange={(event) => update({ type: event.target.value })}
          />
        </label>
      </Toolbar>

      <Panel bodyClassName="py-1">
        {records.isPending ? (
          <LoadingState />
        ) : records.isError ? (
          <ErrorState error={records.error} onRetry={() => void records.refetch()} />
        ) : records.data.items.length === 0 ? (
          <EmptyState
            title={filtered ? t("maintenance.noMatch") : t("overview.noService")}
            body={filtered ? undefined : t("overview.noServiceBody")}
            action={
              canEdit &&
              !filtered && (
                <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
                  {t("maintenance.record")}
                </Button>
              )
            }
          />
        ) : (
          <LogList>
            {records.data.items.map((record) => (
              <LogRow
                key={record.id}
                date={format.date(record.service_date)}
                mileage={record.mileage === null ? "" : format.distance(record.mileage)}
                title={
                  <button
                    type="button"
                    className="text-start hover:text-petrol"
                    onClick={() => setViewing(record)}
                  >
                    {record.title}
                  </button>
                }
                details={
                  <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    {record.title !== record.maintenance_type.name && (
                      <span>{record.maintenance_type.name}</span>
                    )}
                    {record.garage && <span>{record.garage.name}</span>}
                    {record.kind === "repair" && (
                      <Badge tone="due">{t("enums.maintenanceKind.repair")}</Badge>
                    )}
                  </span>
                }
                amount={record.cost === null ? "" : format.money(record.cost, vehicle.currency)}
                actions={
                  <RowMenu
                    label={t("common.moreActions")}
                    actions={[
                      { label: t("common.details"), onSelect: () => setViewing(record) },
                      { label: t("files.title"), onSelect: () => setFiles(record) },
                      canEdit && { label: t("common.edit"), onSelect: () => setEditing(record) },
                      canEdit && {
                        label: t("common.delete"),
                        danger: true,
                        onSelect: () => remove.ask(record),
                      },
                    ]}
                  />
                }
              />
            ))}
          </LogList>
        )}
      </Panel>
      {records.data && (
        <Pagination
          page={records.data.meta.page}
          totalPages={records.data.meta.total_pages}
          total={records.data.meta.total}
          onPageChange={setPage}
        />
      )}

      {editing && (
        <RecordFormDialog
          vehicle={vehicle}
          record={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {viewing && (
        <RecordDetailsDialog vehicle={vehicle} record={viewing} onClose={() => setViewing(null)} />
      )}
      {files && (
        <AttachmentsDialog
          vehicleId={vehicle.id}
          entityType="maintenance_record"
          entityId={files.id}
          title={t("files.of", { name: files.title })}
          canEdit={canEdit}
          onClose={() => setFiles(null)}
        />
      )}
      {remove.dialog}
    </>
  );
}
