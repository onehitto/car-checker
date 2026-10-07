import { useQuery } from "@tanstack/react-query";

import { api, unwrap, unwrapPage } from "@/api/client";
import { vehicleKeys } from "@/features/vehicles/queries";

export function useTires(vehicleId: string) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "tires"),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/vehicles/{vehicle_id}/tires", {
          params: { path: { vehicle_id: vehicleId } },
        }),
      ),
  });
}

export function useTireEvents(vehicleId: string, tireId: string) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "tires", tireId, "events"),
    queryFn: () =>
      unwrapPage(
        api.GET("/api/v1/vehicles/{vehicle_id}/tires/{tire_id}/events", {
          params: { path: { vehicle_id: vehicleId, tire_id: tireId }, query: { limit: 100 } },
        }),
      ),
  });
}
