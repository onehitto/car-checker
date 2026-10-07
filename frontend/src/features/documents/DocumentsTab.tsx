import { Plus } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent } from "@/api/client";
import { DOCUMENT_STATUSES, DOCUMENT_TYPES } from "@/api/enums";
import type { VehicleDocument } from "@/api/types";
import {
  Button,
  EmptyState,
  ErrorState,
  FilterSelect,
  ItemRow,
  LoadingState,
  Panel,
  RowMenu,
  StatusBadge,
  Toolbar,
} from "@/components/ui";
import { AttachmentsDialog } from "@/features/attachments/AttachmentsDialog";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { useFormat } from "@/lib/useFormat";
import { useSearchFilters } from "@/lib/useSearchFilters";

import { DocumentFormDialog } from "./DocumentFormDialog";
import { type DocumentFilters, useDocuments } from "./queries";

/** Insurance, registration, inspection, road tax...: what expires when. */
export function DocumentsTab() {
  const { t } = useTranslation();
  const format = useFormat();
  const { vehicle, canEdit } = useVehicleContext();
  const { values, update } = useSearchFilters({ type: "", status: "" });
  const documents = useDocuments(vehicle.id, {
    document_type: (values.type || undefined) as DocumentFilters["document_type"],
    status: (values.status || undefined) as DocumentFilters["status"],
  });
  const [editing, setEditing] = useState<VehicleDocument | "new" | null>(null);
  const [files, setFiles] = useState<VehicleDocument | null>(null);
  const remove = useConfirmDelete(
    (document: VehicleDocument) =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/documents/{document_id}", {
          params: { path: { vehicle_id: vehicle.id, document_id: document.id } },
        }),
      ),
    { successMessage: t("documents.deleted"), body: t("documents.deleteBody") },
  );
  const filtered = values.type !== "" || values.status !== "";

  const expiry = (document: VehicleDocument) => {
    if (!document.expiration_date) return t("documents.noExpiry");
    const date = format.date(document.expiration_date);
    const days = document.days_until_expiration;
    if (document.status === "expired") return t("documents.expiredOn", { date });
    if (days === 0) return t("documents.expiresToday");
    return days != null && days <= 60
      ? t("documents.expiresIn", { date, days: t("due.days", { count: days }) })
      : t("documents.expiresOn", { date });
  };

  return (
    <>
      <Toolbar
        actions={
          canEdit && (
            <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
              {t("documents.add")}
            </Button>
          )
        }
      >
        <FilterSelect
          label={t("documents.fields.type")}
          value={values.type}
          onChange={(event) => update({ type: event.target.value })}
        >
          <option value="">{t("documents.allTypes")}</option>
          {DOCUMENT_TYPES.map((type) => (
            <option key={type} value={type}>
              {t(`enums.documentType.${type}`)}
            </option>
          ))}
        </FilterSelect>
        <FilterSelect
          label={t("vehicles.status")}
          value={values.status}
          onChange={(event) => update({ status: event.target.value })}
        >
          <option value="">{t("documents.allStatuses")}</option>
          {DOCUMENT_STATUSES.map((status) => (
            <option key={status} value={status}>
              {t(`status.${status}`)}
            </option>
          ))}
        </FilterSelect>
      </Toolbar>
      <Panel bodyClassName="py-1">
        {documents.isPending ? (
          <LoadingState />
        ) : documents.isError ? (
          <ErrorState error={documents.error} onRetry={() => void documents.refetch()} />
        ) : documents.data.items.length === 0 ? (
          <EmptyState
            title={filtered ? t("documents.noMatch") : t("documents.emptyTitle")}
            body={filtered ? undefined : t("documents.emptyBody")}
            action={
              canEdit &&
              !filtered && (
                <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
                  {t("documents.add")}
                </Button>
              )
            }
          />
        ) : (
          <ul className="divide-y divide-rule">
            {documents.data.items.map((document) => (
              <ItemRow
                key={document.id}
                title={document.title}
                details={
                  <span className="flex flex-col">
                    <span>
                      {[
                        t(`enums.documentType.${document.document_type}`),
                        document.provider,
                        document.document_number,
                      ]
                        .filter(Boolean)
                        .join(", ")}
                    </span>
                    <span>{expiry(document)}</span>
                  </span>
                }
                aside={
                  document.expiration_date && <StatusBadge status={document.status ?? "valid"} />
                }
                actions={
                  <RowMenu
                    label={t("common.moreActions")}
                    actions={[
                      { label: t("files.title"), onSelect: () => setFiles(document) },
                      canEdit && { label: t("common.edit"), onSelect: () => setEditing(document) },
                      canEdit && {
                        label: t("common.delete"),
                        danger: true,
                        onSelect: () => remove.ask(document),
                      },
                    ]}
                  />
                }
              />
            ))}
          </ul>
        )}
      </Panel>
      {editing && (
        <DocumentFormDialog
          vehicle={vehicle}
          document={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {files && (
        <AttachmentsDialog
          vehicleId={vehicle.id}
          entityType="vehicle_document"
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
