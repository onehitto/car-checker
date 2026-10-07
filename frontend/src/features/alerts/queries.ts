import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, unwrap, unwrapPage } from "@/api/client";
import type { Alert } from "@/api/types";

export const alertKeys = {
  all: ["alerts"] as const,
  summary: ["alerts", "summary"] as const,
  list: (filters: object) => ["alerts", "list", filters] as const,
};

export function useAlertSummary() {
  return useQuery({
    queryKey: alertKeys.summary,
    queryFn: () => unwrap(api.GET("/api/v1/alerts/summary")),
    refetchInterval: 60_000,
  });
}

export interface AlertFilters {
  page: number;
  status?: Alert["status"][];
  priority?: Alert["priority"][];
  vehicle_id?: string;
}

export function useAlerts(filters: AlertFilters) {
  return useQuery({
    queryKey: alertKeys.list(filters),
    queryFn: () =>
      unwrapPage(api.GET("/api/v1/alerts", { params: { query: { ...filters, limit: 20 } } })),
    placeholderData: keepPreviousData,
  });
}
