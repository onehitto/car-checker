import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, unwrap, unwrapPage } from "@/api/client";
import type { MaintenanceRecord } from "@/api/types";
import { vehicleKeys } from "@/features/vehicles/queries";

export interface RecordFilters {
  page: number;
  kind?: MaintenanceRecord["kind"];
  maintenance_type_id?: string;
  q?: string;
}

export function useMaintenanceRecords(vehicleId: string, filters: RecordFilters) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "maintenance", filters),
    queryFn: () =>
      unwrapPage(
        api.GET("/api/v1/vehicles/{vehicle_id}/maintenance", {
          params: {
            path: { vehicle_id: vehicleId },
            query: { ...filters, limit: 20, sort: "-service_date" },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}

export function useSchedules(vehicleId: string) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "schedules"),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/vehicles/{vehicle_id}/maintenance-schedules", {
          params: { path: { vehicle_id: vehicleId } },
        }),
      ),
  });
}

export function useOilChanges(vehicleId: string, page: number) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "oil-changes", page),
    queryFn: () =>
      unwrapPage(
        api.GET("/api/v1/vehicles/{vehicle_id}/oil-changes", {
          params: { path: { vehicle_id: vehicleId }, query: { page, limit: 20 } },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}
