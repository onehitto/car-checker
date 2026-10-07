import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, unwrap, unwrapPage } from "@/api/client";

/** Every vehicle-scoped query key starts with ["vehicles", vehicleId]. */
export const vehicleKeys = {
  all: ["vehicles"] as const,
  list: (params: object) => ["vehicles", "list", params] as const,
  detail: (id: string) => ["vehicles", id] as const,
  part: (id: string, ...rest: unknown[]) => ["vehicles", id, ...rest] as const,
};

interface VehicleListParams {
  q?: string;
  status?: "active" | "sold" | "archived";
  page?: number;
  limit?: number;
  sort?: string;
}

export function useVehicleList(params: VehicleListParams = {}) {
  return useQuery({
    queryKey: vehicleKeys.list(params),
    queryFn: () => unwrapPage(api.GET("/api/v1/vehicles", { params: { query: params } })),
    placeholderData: keepPreviousData,
  });
}

export function useVehicle(vehicleId: string) {
  return useQuery({
    queryKey: vehicleKeys.detail(vehicleId),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/vehicles/{vehicle_id}", { params: { path: { vehicle_id: vehicleId } } }),
      ),
  });
}

export function useVehicleDashboard(vehicleId: string) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "dashboard"),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/vehicles/{vehicle_id}/dashboard", {
          params: { path: { vehicle_id: vehicleId } },
        }),
      ),
  });
}
