import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, unwrapPage } from "@/api/client";
import { vehicleKeys } from "@/features/vehicles/queries";

export interface PartFilters {
  page: number;
  installed?: boolean;
  part_type_id?: string;
}

export function useParts(vehicleId: string, filters: PartFilters) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "parts", filters),
    queryFn: () =>
      unwrapPage(
        api.GET("/api/v1/vehicles/{vehicle_id}/parts", {
          params: {
            path: { vehicle_id: vehicleId },
            query: { ...filters, limit: 20, sort: "-installed_date" },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}
