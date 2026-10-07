import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, unwrapPage } from "@/api/client";
import { vehicleKeys } from "@/features/vehicles/queries";

export function useMileageEntries(vehicleId: string, page: number, limit = 20) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "mileage", page, limit),
    queryFn: () =>
      unwrapPage(
        api.GET("/api/v1/vehicles/{vehicle_id}/mileage", {
          params: { path: { vehicle_id: vehicleId }, query: { page, limit } },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}
