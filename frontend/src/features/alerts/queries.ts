import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "@/api/client";

export const alertKeys = {
  all: ["alerts"] as const,
  summary: ["alerts", "summary"] as const,
};

export function useAlertSummary() {
  return useQuery({
    queryKey: alertKeys.summary,
    queryFn: () => unwrap(api.GET("/api/v1/alerts/summary")),
    refetchInterval: 60_000,
  });
}
