import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Dialog, ErrorState, LoadingState } from "@/components/ui";

import { AttachmentList } from "./AttachmentList";
import { type AttachmentEntity, useAttachments } from "./queries";
import { UploadButton } from "./UploadButton";

interface AttachmentsDialogProps {
  vehicleId: string;
  entityType: AttachmentEntity;
  entityId: string;
  title: ReactNode;
  canEdit: boolean;
  onClose: () => void;
}

/** Invoices, photos and scans of one record (service, document, expense...). */
export function AttachmentsDialog({
  vehicleId,
  entityType,
  entityId,
  title,
  canEdit,
  onClose,
}: AttachmentsDialogProps) {
  const { t } = useTranslation();
  const files = useAttachments(vehicleId, { entity_type: entityType, entity_id: entityId });
  return (
    <Dialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={title}
      description={t("files.dialogBody")}
    >
      {files.isPending ? (
        <LoadingState />
      ) : files.isError ? (
        <ErrorState error={files.error} onRetry={() => void files.refetch()} />
      ) : files.data.items.length === 0 ? (
        <p className="py-2 text-steel">{t("files.noneForRecord")}</p>
      ) : (
        <AttachmentList vehicleId={vehicleId} items={files.data.items} canEdit={canEdit} />
      )}
      {canEdit && (
        <div className="mt-4 flex flex-col items-start gap-1.5">
          <UploadButton
            vehicleId={vehicleId}
            entityType={entityType}
            entityId={entityId}
            variant="secondary"
          />
          <p className="text-sm text-steel">{t("files.hint")}</p>
        </div>
      )}
    </Dialog>
  );
}
