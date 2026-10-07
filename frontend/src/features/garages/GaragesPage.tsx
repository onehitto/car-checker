import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent, unwrapPage } from "@/api/client";
import { GARAGE_TYPES } from "@/api/enums";
import type { Garage } from "@/api/types";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  FilterSelect,
  Input,
  ItemRow,
  LoadingState,
  PageHeader,
  Pagination,
  Panel,
  RowMenu,
  Toolbar,
} from "@/components/ui";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { useSearchFilters } from "@/lib/useSearchFilters";

import { GarageFormDialog } from "./GarageFormDialog";

/** /garages — the garages, mechanics and shops the user works with. */
export function GaragesPage() {
  const { t } = useTranslation();
  const { values, page, update, setPage } = useSearchFilters({ q: "", type: "" });
  const search = useDeferredValue(values.q);
  const filters = {
    page,
    limit: 20,
    sort: "name",
    q: search || undefined,
    garage_type: (values.type || undefined) as Garage["garage_type"] | undefined,
  };
  const garages = useQuery({
    queryKey: ["garages", "list", filters],
    queryFn: () => unwrapPage(api.GET("/api/v1/garages", { params: { query: filters } })),
    placeholderData: keepPreviousData,
  });
  const [editing, setEditing] = useState<Garage | "new" | null>(null);
  const remove = useConfirmDelete(
    (garage: Garage) =>
      expectNoContent(
        api.DELETE("/api/v1/garages/{garage_id}", {
          params: { path: { garage_id: garage.id } },
        }),
      ),
    { successMessage: t("garages.deleted"), body: t("garages.deleteBody") },
  );
  const filtered = values.q !== "" || values.type !== "";

  return (
    <>
      <PageHeader
        title={t("garages.title")}
        description={t("garages.description")}
        actions={
          <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
            {t("garages.add")}
          </Button>
        }
      />
      <Toolbar>
        <label className="relative min-w-48 flex-1 sm:max-w-xs">
          <span className="sr-only">{t("common.search")}</span>
          <Search
            className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-steel"
            aria-hidden="true"
          />
          <Input
            type="search"
            className="ps-9"
            placeholder={t("garages.searchPlaceholder")}
            value={values.q}
            onChange={(event) => update({ q: event.target.value })}
          />
        </label>
        <FilterSelect
          label={t("garages.fields.type")}
          value={values.type}
          onChange={(event) => update({ type: event.target.value })}
        >
          <option value="">{t("garages.allTypes")}</option>
          {GARAGE_TYPES.map((type) => (
            <option key={type} value={type}>
              {t(`enums.garageType.${type}`)}
            </option>
          ))}
        </FilterSelect>
      </Toolbar>
      <Panel bodyClassName="py-1">
        {garages.isPending ? (
          <LoadingState />
        ) : garages.isError ? (
          <ErrorState error={garages.error} onRetry={() => void garages.refetch()} />
        ) : garages.data.items.length === 0 ? (
          <EmptyState
            title={filtered ? t("garages.noMatch") : t("garages.emptyTitle")}
            body={filtered ? undefined : t("garages.emptyBody")}
          />
        ) : (
          <ul className="divide-y divide-rule">
            {garages.data.items.map((garage) => (
              <ItemRow
                key={garage.id}
                title={
                  <span className="flex flex-wrap items-center gap-2">
                    {garage.name}
                    <Badge tone="neutral">{t(`enums.garageType.${garage.garage_type}`)}</Badge>
                  </span>
                }
                details={
                  <span className="flex flex-wrap gap-x-4">
                    {[garage.address, garage.city, garage.country].filter(Boolean).join(", ") && (
                      <span>
                        {[garage.address, garage.city, garage.country].filter(Boolean).join(", ")}
                      </span>
                    )}
                    {garage.contact_name && <span>{garage.contact_name}</span>}
                    {garage.phone && (
                      <a
                        href={`tel:${garage.phone}`}
                        dir="ltr"
                        className="text-petrol hover:underline"
                      >
                        {garage.phone}
                      </a>
                    )}
                    {garage.email && (
                      <a href={`mailto:${garage.email}`} className="text-petrol hover:underline">
                        {garage.email}
                      </a>
                    )}
                    {garage.website && (
                      <a
                        href={garage.website}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="text-petrol hover:underline"
                      >
                        {garage.website.replace(/^https?:\/\//, "")}
                      </a>
                    )}
                  </span>
                }
                actions={
                  <RowMenu
                    label={t("common.moreActions")}
                    actions={[
                      { label: t("common.edit"), onSelect: () => setEditing(garage) },
                      {
                        label: t("common.delete"),
                        danger: true,
                        onSelect: () => remove.ask(garage),
                      },
                    ]}
                  />
                }
              />
            ))}
          </ul>
        )}
      </Panel>
      {garages.data && (
        <Pagination
          page={garages.data.meta.page}
          totalPages={garages.data.meta.total_pages}
          total={garages.data.meta.total}
          onPageChange={setPage}
        />
      )}
      {editing && (
        <GarageFormDialog
          garage={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {remove.dialog}
    </>
  );
}
