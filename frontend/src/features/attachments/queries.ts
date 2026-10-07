import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, unwrapPage } from "@/api/client";
import type { Attachment } from "@/api/types";
import { vehicleKeys } from "@/features/vehicles/queries";

export type AttachmentEntity = Attachment["entity_type"];

interface AttachmentFilters {
  page?: number;
  entity_type?: AttachmentEntity;
  entity_id?: string;
}

export function useAttachments(vehicleId: string, filters: AttachmentFilters) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "attachments", filters),
    queryFn: () =>
      unwrapPage(
        api.GET("/api/v1/vehicles/{vehicle_id}/attachments", {
          params: {
            path: { vehicle_id: vehicleId },
            query: { ...filters, limit: filters.entity_id ? 100 : 20 },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}
