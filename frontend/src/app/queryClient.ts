import { MutationCache, QueryClient } from "@tanstack/react-query";

import { isApiError } from "@/api/errors";

declare module "@tanstack/react-query" {
  interface Register {
    mutationMeta: {
      /** Set to false when the mutation refreshes the cache itself (e.g. deleting a vehicle). */
      invalidate?: boolean;
    };
    queryMeta: {
      /** The data is an object URL to release when the query leaves the cache. */
      objectUrl?: boolean;
    };
  }
}

export function createQueryClient(): QueryClient {
  const queryClient: QueryClient = new QueryClient({
    mutationCache: new MutationCache({
      // One write can change derived data anywhere (mileage, due dates, alerts, dashboards,
      // statistics), so every successful write refreshes the queries on screen.
      onSuccess: (_data, _variables, _context, mutation) =>
        mutation.meta?.invalidate === false
          ? undefined
          : // Stored files never change: keep their object URLs.
            queryClient.invalidateQueries({ predicate: (query) => !query.meta?.objectUrl }),
    }),
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        // Client errors (4xx) will not fix themselves: only retry network and server errors.
        retry: (failureCount, error) =>
          failureCount < 2 && !(isApiError(error) && error.status >= 400 && error.status < 500),
      },
      mutations: { retry: false },
    },
  });
  queryClient.getQueryCache().subscribe((event) => {
    const { meta, state } = event.query;
    if (event.type === "removed" && meta?.objectUrl && typeof state.data === "string") {
      URL.revokeObjectURL(state.data);
    }
  });
  return queryClient;
}
