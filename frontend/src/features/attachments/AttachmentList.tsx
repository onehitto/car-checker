import { useMutation } from "@tanstack/react-query";
import { FileImage, FileText } from "lucide-react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent } from "@/api/client";
import { downloadFile } from "@/api/files";
import type { Attachment } from "@/api/types";
import { errorMessage, RowMenu, useToast } from "@/components/ui";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { useFormat } from "@/lib/useFormat";

interface AttachmentListProps {
  vehicleId: string;
  items: Attachment[];
  canEdit: boolean;
  /** Show what each file belongs to (vehicle-wide list). */
  showEntity?: boolean;
}

export function AttachmentList({ vehicleId, items, canEdit, showEntity }: AttachmentListProps) {
  const { t } = useTranslation();
  const toast = useToast();
  const format = useFormat();
  const download = useMutation({
    mutationFn: (attachment: Attachment) =>
      downloadFile(
        `/api/v1/vehicles/${vehicleId}/attachments/${attachment.id}/download`,
        attachment.file_name,
      ),
    onError: (error) => toast.error(errorMessage(error, t)),
  });
  const remove = useConfirmDelete(
    (attachment: Attachment) =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/attachments/{attachment_id}", {
          params: { path: { vehicle_id: vehicleId, attachment_id: attachment.id } },
        }),
      ),
    { successMessage: t("files.deleted"), body: t("files.deleteBody") },
  );

  return (
    <>
      <ul className="divide-y divide-rule">
        {items.map((attachment) => {
          const Icon = attachment.content_type.startsWith("image/") ? FileImage : FileText;
          return (
            <li key={attachment.id} className="flex items-center gap-3 py-3">
              <Icon className="size-5 shrink-0 text-steel" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <button
                  type="button"
                  className="max-w-full truncate text-start font-medium hover:text-petrol"
                  onClick={() => download.mutate(attachment)}
                >
                  {attachment.file_name}
                </button>
                <p className="flex flex-wrap gap-x-3 text-sm text-steel">
                  <span className="numeric">{format.bytes(attachment.file_size)}</span>
                  <span className="numeric">{format.date(attachment.uploaded_at)}</span>
                  {showEntity && (
                    <span>{t(`enums.attachmentEntity.${attachment.entity_type}`)}</span>
                  )}
                </p>
              </div>
              <RowMenu
                label={t("common.moreActions")}
                actions={[
                  { label: t("files.download"), onSelect: () => download.mutate(attachment) },
                  canEdit && {
                    label: t("common.delete"),
                    danger: true,
                    onSelect: () => remove.ask(attachment),
                  },
                ]}
              />
            </li>
          );
        })}
      </ul>
      {remove.dialog}
    </>
  );
}
