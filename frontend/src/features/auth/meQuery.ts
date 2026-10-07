import { api, unwrap } from "@/api/client";

export const ME_QUERY_KEY = ["me"] as const;

export function fetchMe() {
  return unwrap(api.GET("/api/v1/users/me"));
}
