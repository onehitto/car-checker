import { useMutation } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import { useRef } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "@/api/errors";
import { sendForm } from "@/api/files";
import type { Attachment } from "@/api/types";
import { Button, errorMessage, useToast } from "@/components/ui";

import { FILE_TYPES, MAX_FILE_SIZE } from "./fileTypes";
import type { AttachmentEntity } from "./queries";

interface UploadButtonProps {
  vehicleId: string;
  entityType: AttachmentEntity;
  entityId?: string;
  label?: string;
  variant?: "primary" | "secondary";
}

/** Pick one or more files (PDF or images) and attach them to a vehicle or one of its records. */
export function UploadButton({
  vehicleId,
  entityType,
  entityId,
  label,
  variant = "primary",
}: UploadButtonProps) {
  const { t } = useTranslation();
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);

  const upload = useMutation({
    mutationFn: async (files: File[]) => {
      for (const file of files) {
        if (file.size > MAX_FILE_SIZE) {
          throw new ApiError(413, { code: "PAYLOAD_TOO_LARGE", message: file.name });
        }
        const body = new FormData();
        body.append("file", file);
        body.append("entity_type", entityType);
        if (entityId) body.append("entity_id", entityId);
        await sendForm<Attachment>("POST", `/api/v1/vehicles/${vehicleId}/attachments`, body);
      }
      return files.length;
    },
    onSuccess: (count) => toast.success(t("files.uploaded", { count })),
    onError: (error) => toast.error(errorMessage(error, t)),
  });

  return (
    <>
      <input
        ref={input}
        type="file"
        multiple
        accept={FILE_TYPES}
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          if (files.length > 0) upload.mutate(files);
          event.target.value = "";
        }}
      />
      <Button
        variant={variant}
        icon={<Upload className="size-4" />}
        loading={upload.isPending}
        onClick={() => input.current?.click()}
      >
        {label ?? t("files.add")}
      </Button>
    </>
  );
}
