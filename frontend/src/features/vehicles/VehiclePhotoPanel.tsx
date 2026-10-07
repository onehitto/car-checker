import { useMutation } from "@tanstack/react-query";
import { Camera, CarFront } from "lucide-react";
import { useRef } from "react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent } from "@/api/client";
import { sendForm } from "@/api/files";
import type { Vehicle } from "@/api/types";
import { Button, errorMessage, Panel, useToast } from "@/components/ui";
import { IMAGE_TYPES } from "@/features/attachments/fileTypes";
import { useAttachmentUrl } from "@/features/attachments/useAttachmentUrl";

import { vehicleContextFor } from "./vehicleContext";

export function VehiclePhotoPanel({ vehicle }: { vehicle: Vehicle }) {
  const { t } = useTranslation();
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const photo = useAttachmentUrl(vehicle.id, vehicle.image_attachment_id);
  const { canEdit } = vehicleContextFor(vehicle);

  const upload = useMutation({
    mutationFn: (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return sendForm<Vehicle>("PUT", `/api/v1/vehicles/${vehicle.id}/image`, body);
    },
    onSuccess: () => toast.success(t("vehicles.photo.saved")),
    onError: (error) => toast.error(errorMessage(error, t)),
  });
  const remove = useMutation({
    mutationFn: () =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/image", {
          params: { path: { vehicle_id: vehicle.id } },
        }),
      ),
    onSuccess: () => toast.success(t("vehicles.photo.removed")),
    onError: (error) => toast.error(errorMessage(error, t)),
  });

  return (
    <Panel title={t("vehicles.photo.title")} bodyClassName="flex flex-col gap-3">
      <div className="grid aspect-[4/3] place-items-center overflow-hidden rounded-md bg-paper">
        {photo.data ? (
          <img src={photo.data} alt={vehicle.display_name} className="size-full object-cover" />
        ) : (
          <CarFront className="size-12 text-rule" aria-hidden="true" />
        )}
      </div>
      {canEdit && (
        <div className="flex flex-wrap gap-2">
          <input
            ref={input}
            type="file"
            accept={IMAGE_TYPES}
            className="sr-only"
            tabIndex={-1}
            aria-hidden="true"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) upload.mutate(file);
              event.target.value = "";
            }}
          />
          <Button
            variant="secondary"
            size="sm"
            icon={<Camera className="size-4" />}
            loading={upload.isPending}
            onClick={() => input.current?.click()}
          >
            {vehicle.image_attachment_id ? t("vehicles.photo.change") : t("vehicles.photo.add")}
          </Button>
          {vehicle.image_attachment_id && (
            <Button
              variant="ghost"
              size="sm"
              loading={remove.isPending}
              onClick={() => remove.mutate()}
            >
              {t("vehicles.photo.remove")}
            </Button>
          )}
        </div>
      )}
      <p className="text-sm text-steel">{t("vehicles.photo.hint")}</p>
    </Panel>
  );
}
