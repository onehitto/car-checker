import { Plus } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent } from "@/api/client";
import type { Part } from "@/api/types";
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
  StatusBadge,
  Toolbar,
} from "@/components/ui";
import { AttachmentsDialog } from "@/features/attachments/AttachmentsDialog";
import { PartTypeSelect } from "@/features/catalog/selects";
import { useDueText } from "@/features/maintenance/useDueText";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { useFormat } from "@/lib/useFormat";
import { useSearchFilters } from "@/lib/useSearchFilters";

import { PartFormDialog } from "./PartFormDialog";
import { useParts } from "./queries";
import { RemovePartDialog } from "./RemovePartDialog";

/** Parts fitted to the vehicle, with their expected lifetime. */
export function PartsTab() {
  const { t } = useTranslation();
  const format = useFormat();
  const dueText = useDueText();
  const { vehicle, canEdit } = useVehicleContext();
  const { values, page, update, setPage } = useSearchFilters({ installed: "true", type: "" });
  const parts = useParts(vehicle.id, {
    page,
    installed: values.installed === "" ? undefined : values.installed === "true",
    part_type_id: values.type || undefined,
  });
  const [editing, setEditing] = useState<Part | "new" | null>(null);
  const [removing, setRemoving] = useState<Part | null>(null);
  const [files, setFiles] = useState<Part | null>(null);
  const remove = useConfirmDelete(
    (part: Part) =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/parts/{part_id}", {
          params: { path: { vehicle_id: vehicle.id, part_id: part.id } },
        }),
      ),
    { successMessage: t("parts.deleted"), body: t("parts.deleteBody") },
  );

  return (
    <>
      <Toolbar
        actions={
          canEdit && (
            <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
              {t("parts.add")}
            </Button>
          )
        }
      >
        <FilterSelect
          label={t("parts.fitted")}
          value={values.installed}
          onChange={(event) => update({ installed: event.target.value })}
        >
          <option value="true">{t("parts.filterFitted")}</option>
          <option value="false">{t("parts.filterRemoved")}</option>
          <option value="">{t("parts.filterAll")}</option>
        </FilterSelect>
        <label>
          <span className="sr-only">{t("maintenance.fields.type")}</span>
          <PartTypeSelect
            className="w-auto min-w-48"
            placeholder={t("maintenance.allTypes")}
            value={values.type}
            onChange={(event) => update({ type: event.target.value })}
          />
        </label>
      </Toolbar>
      <Panel bodyClassName="py-1">
        {parts.isPending ? (
          <LoadingState />
        ) : parts.isError ? (
          <ErrorState error={parts.error} onRetry={() => void parts.refetch()} />
        ) : parts.data.items.length === 0 ? (
          <EmptyState title={t("parts.emptyTitle")} body={t("parts.emptyBody")} />
        ) : (
          <LogList>
            {parts.data.items.map((part) => (
              <LogRow
                key={part.id}
                date={format.date(part.installed_date)}
                mileage={
                  part.installed_mileage === null ? "" : format.distance(part.installed_mileage)
                }
                title={
                  <span className="flex flex-wrap items-center gap-2">
                    {part.quantity > 1 ? `${part.quantity} × ${part.part_name}` : part.part_name}
                    {part.is_installed && part.lifetime && part.lifetime.status !== "unknown" && (
                      <StatusBadge status={part.lifetime.status} />
                    )}
                    {!part.is_installed && <Badge tone="neutral">{t("parts.removedBadge")}</Badge>}
                  </span>
                }
                details={
                  <span className="flex flex-col">
                    <span>
                      {[part.brand, part.reference_number, part.position, part.garage?.name]
                        .filter(Boolean)
                        .join(", ")}
                    </span>
                    {part.is_installed && part.lifetime && part.lifetime.status !== "unknown" && (
                      <span>{t("parts.replace", { due: dueText(part.lifetime) })}</span>
                    )}
                    {!part.is_installed && part.removed_date && (
                      <span>{t("parts.removedOn", { date: format.date(part.removed_date) })}</span>
                    )}
                  </span>
                }
                amount={
                  part.total_cost === null ? "" : format.money(part.total_cost, vehicle.currency)
                }
                actions={
                  <RowMenu
                    label={t("common.moreActions")}
                    actions={[
                      { label: t("files.title"), onSelect: () => setFiles(part) },
                      canEdit && { label: t("common.edit"), onSelect: () => setEditing(part) },
                      canEdit &&
                        part.is_installed && {
                          label: t("parts.remove"),
                          onSelect: () => setRemoving(part),
                        },
                      canEdit && {
                        label: t("common.delete"),
                        danger: true,
                        onSelect: () => remove.ask(part),
                      },
                    ]}
                  />
                }
              />
            ))}
          </LogList>
        )}
      </Panel>
      {parts.data && (
        <Pagination
          page={parts.data.meta.page}
          totalPages={parts.data.meta.total_pages}
          total={parts.data.meta.total}
          onPageChange={setPage}
        />
      )}
      {editing && (
        <PartFormDialog
          vehicle={vehicle}
          part={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {removing && (
        <RemovePartDialog vehicle={vehicle} part={removing} onClose={() => setRemoving(null)} />
      )}
      {files && (
        <AttachmentsDialog
          vehicleId={vehicle.id}
          entityType="part_replacement"
          entityId={files.id}
          title={t("files.of", { name: files.part_name })}
          canEdit={canEdit}
          onClose={() => setFiles(null)}
        />
      )}
      {remove.dialog}
    </>
  );
}
