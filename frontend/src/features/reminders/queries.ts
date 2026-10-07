import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "@/api/client";
import { vehicleKeys } from "@/features/vehicles/queries";

export function useReminders(vehicleId: string, completed: boolean) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "reminders", completed),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/vehicles/{vehicle_id}/reminders", {
          params: { path: { vehicle_id: vehicleId }, query: { completed } },
        }),
      ),
  });
}
