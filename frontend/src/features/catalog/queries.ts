import { useQuery } from "@tanstack/react-query";

import { api, unwrap, unwrapPage } from "@/api/client";

/** System types (translated by the API) followed by the user's custom types. */
export function useMaintenanceTypes() {
  return useQuery({
    queryKey: ["maintenance-types"],
    queryFn: () => unwrap(api.GET("/api/v1/maintenance-types")),
    staleTime: 5 * 60_000,
  });
}

export function usePartTypes() {
  return useQuery({
    queryKey: ["part-types"],
    queryFn: () => unwrap(api.GET("/api/v1/part-types")),
    staleTime: 5 * 60_000,
  });
}

/** The user's garages, for selects. */
export function useGarageOptions() {
  return useQuery({
    queryKey: ["garages", "options"],
    queryFn: () =>
      unwrapPage(api.GET("/api/v1/garages", { params: { query: { limit: 100, sort: "name" } } })),
    select: (page) => page.items,
  });
}
