import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api, unwrapPage } from "@/api/client";
import type { Expense } from "@/api/types";
import { vehicleKeys } from "@/features/vehicles/queries";

export interface ExpenseFilters {
  page: number;
  category?: Expense["category"][];
  q?: string;
}

export function useExpenses(vehicleId: string, filters: ExpenseFilters) {
  return useQuery({
    queryKey: vehicleKeys.part(vehicleId, "expenses", filters),
    queryFn: () =>
      unwrapPage(
        api.GET("/api/v1/vehicles/{vehicle_id}/expenses", {
          params: {
            path: { vehicle_id: vehicleId },
            query: { ...filters, limit: 20, sort: "-expense_date" },
          },
        }),
      ),
    placeholderData: keepPreviousData,
  });
}
