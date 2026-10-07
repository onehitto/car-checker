import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, unwrap, unwrapPage } from "@/api/client";
import type { User } from "@/api/types";
import { vehicleKeys } from "@/features/vehicles/queries";

export function useFuelRecords(vehicleId: string, page: number) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "fuel", page),
    queryFn: () =>
      unwrapPage(
        api.GET("/api/v1/vehicles/{vehicle_id}/fuel", {
          params: { path: { vehicle_id: vehicleId }, query: { page, limit: 20 } },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

/** Statistics in the user's distance and consumption units. */
export function useFuelStatistics(vehicleId: string, user: User) {
  const units = {
    distance_unit: user.preferred_distance_unit,
    consumption_unit: user.preferred_consumption_unit,
  };
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "fuel-statistics", units),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/vehicles/{vehicle_id}/fuel/statistics", {
          params: { path: { vehicle_id: vehicleId }, query: units },
        }),
      ),
  });
}
