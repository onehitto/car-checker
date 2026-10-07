import { useQuery } from "@tanstack/react-query";

import { api, unwrapPage } from "@/api/client";
import type { VehicleDocument } from "@/api/types";
import { vehicleKeys } from "@/features/vehicles/queries";

export interface DocumentFilters {
  document_type?: VehicleDocument["document_type"];
  status?: NonNullable<VehicleDocument["status"]>;
}

export function useDocuments(vehicleId: string, filters: DocumentFilters) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "documents", filters),
    queryFn: () =>
      unwrapPage(
        api.GET("/api/v1/vehicles/{vehicle_id}/documents", {
          params: {
            path: { vehicle_id: vehicleId },
            query: { ...filters, limit: 100, sort: "expiration_date" },
          },
        }),
      ),
  });
}
