import { useSearchParams } from "react-router";

/**
 * List filters kept in the URL (shareable, survive reloads). Changing a filter returns to the
 * first page.
 */
export function useSearchFilters<K extends string>(defaults: Record<K, string>) {
  const [params, setParams] = useSearchParams();
  const values = Object.fromEntries(
    Object.entries<string>(defaults).map(([key, fallback]) => [key, params.get(key) ?? fallback]),
  ) as Record<K, string>;
  const page = Math.max(1, Number(params.get("page") ?? 1) || 1);

  function update(changes: Partial<Record<K | "page", string>>) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries<string | undefined>(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (!("page" in changes)) next.delete("page");
    setParams(next, { replace: true });
  }

  return {
    values,
    page,
    update,
    setPage: (next: number) => update({ page: String(next) } as never),
  };
}
