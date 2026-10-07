import { useTranslation } from "react-i18next";

import { ATTACHMENT_ENTITIES } from "@/api/enums";
import {
  EmptyState,
  ErrorState,
  FilterSelect,
  LoadingState,
  Pagination,
  Panel,
  Toolbar,
} from "@/components/ui";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { useSearchFilters } from "@/lib/useSearchFilters";

import { AttachmentList } from "./AttachmentList";
import { type AttachmentEntity, useAttachments } from "./queries";
import { UploadButton } from "./UploadButton";

/** Every file of the vehicle: its own papers and the ones attached to its records. */
export function FilesTab() {
  const { t } = useTranslation();
  const { vehicle, canEdit } = useVehicleContext();
  const { values, page, update, setPage } = useSearchFilters({ entity: "" });
  const files = useAttachments(vehicle.id, {
    page,
    entity_type: (values.entity || undefined) as AttachmentEntity | undefined,
  });

  return (
    <>
      <Toolbar actions={canEdit && <UploadButton vehicleId={vehicle.id} entityType="vehicle" />}>
        <FilterSelect
          label={t("files.belongsTo")}
          value={values.entity}
          onChange={(event) => update({ entity: event.target.value })}
        >
          <option value="">{t("files.allFiles")}</option>
          {ATTACHMENT_ENTITIES.map((entity) => (
            <option key={entity} value={entity}>
              {t(`enums.attachmentEntity.${entity}`)}
            </option>
          ))}
        </FilterSelect>
      </Toolbar>
      <Panel bodyClassName="py-1">
        {files.isPending ? (
          <LoadingState />
        ) : files.isError ? (
          <ErrorState error={files.error} onRetry={() => void files.refetch()} />
        ) : files.data.items.length === 0 ? (
          <EmptyState title={t("files.emptyTitle")} body={t("files.emptyBody")} />
        ) : (
          <AttachmentList
            vehicleId={vehicle.id}
            items={files.data.items}
            canEdit={canEdit}
            showEntity
          />
        )}
      </Panel>
      {files.data && (
        <Pagination
          page={files.data.meta.page}
          totalPages={files.data.meta.total_pages}
          total={files.data.meta.total}
          onPageChange={setPage}
        />
      )}
    </>
  );
}
