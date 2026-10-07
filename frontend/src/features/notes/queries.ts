import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, unwrapPage } from "@/api/client";
import type { Note } from "@/api/types";
import { vehicleKeys } from "@/features/vehicles/queries";

export interface NoteFilters {
  page: number;
  category?: Note["category"];
  q?: string;
}

export function useNotes(vehicleId: string, filters: NoteFilters) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "notes", filters),
    queryFn: () =>
      unwrapPage(
        api.GET("/api/v1/vehicles/{vehicle_id}/notes", {
          params: { path: { vehicle_id: vehicleId }, query: { ...filters, limit: 20 } },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}
