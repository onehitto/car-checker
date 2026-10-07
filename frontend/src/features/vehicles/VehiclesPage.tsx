import { ChevronRight, Plus, Search } from "lucide-react";
import { useDeferredValue } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router";

import { VEHICLE_STATUSES } from "@/api/enums";
import type { Vehicle } from "@/api/types";
import {
  Badge,
  ButtonLink,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  PageHeader,
  Pagination,
  Plate,
  Select,
} from "@/components/ui";
import { useFormat } from "@/lib/useFormat";

import { vehicleDescription } from "./describe";
import { useVehicleList } from "./queries";

const PAGE_SIZE = 20;

export function VehiclesPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const status = params.get("status") ?? "active";
  const page = Number(params.get("page") ?? 1);
  const search = useDeferredValue(q);

  const vehicles = useVehicleList({
    q: search || undefined,
    status: status === "all" ? undefined : (status as Vehicle["status"]),
    page,
    limit: PAGE_SIZE,
    sort: "created_at",
  });

  function update(changes: Record<string, string>) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (!("page" in changes)) next.delete("page");
    setParams(next, { replace: true });
  }

  const filtered = q !== "" || status !== "active";
  const items = vehicles.data?.items ?? [];

  return (
    <>
      <PageHeader
        title={t("vehicles.title")}
        actions={
          <ButtonLink to="/vehicles/new" variant="primary" icon={<Plus className="size-4" />}>
            {t("nav.addVehicle")}
          </ButtonLink>
        }
      />
      <div className="mb-4 flex flex-wrap gap-3">
        <label className="relative min-w-56 flex-1">
          <span className="sr-only">{t("common.search")}</span>
          <Search
            className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-steel"
            aria-hidden="true"
          />
          <Input
            type="search"
            value={q}
            placeholder={t("vehicles.searchPlaceholder")}
            onChange={(event) => update({ q: event.target.value })}
            className="ps-9"
          />
        </label>
        <label className="w-44">
          <span className="sr-only">{t("vehicles.status")}</span>
          <Select value={status} onChange={(event) => update({ status: event.target.value })}>
            {VEHICLE_STATUSES.map((value) => (
              <option key={value} value={value}>
                {t(`enums.vehicleStatus.${value}`)}
              </option>
            ))}
            <option value="all">{t("common.all")}</option>
          </Select>
        </label>
      </div>

      {vehicles.isPending ? (
        <LoadingState />
      ) : vehicles.isError ? (
        <ErrorState error={vehicles.error} onRetry={() => void vehicles.refetch()} />
      ) : items.length === 0 ? (
        filtered ? (
          <EmptyState title={t("vehicles.noMatch")} body={t("vehicles.noMatchBody")} />
        ) : (
          <EmptyState
            title={t("vehicles.emptyTitle")}
            body={t("vehicles.emptyBody")}
            action={
              <ButtonLink to="/vehicles/new" variant="primary" icon={<Plus className="size-4" />}>
                {t("nav.addVehicle")}
              </ButtonLink>
            }
          />
        )
      ) : (
        <>
          <ul className="divide-y divide-rule rounded-panel border border-rule bg-sheet">
            {items.map((vehicle) => (
              <VehicleRow key={vehicle.id} vehicle={vehicle} />
            ))}
          </ul>
          <Pagination
            page={vehicles.data.meta.page}
            totalPages={vehicles.data.meta.total_pages}
            total={vehicles.data.meta.total}
            onPageChange={(next) => update({ page: String(next) })}
          />
        </>
      )}
    </>
  );
}

function VehicleRow({ vehicle }: { vehicle: Vehicle }) {
  const { t } = useTranslation();
  const format = useFormat();
  const role = vehicle.access_role;
  return (
    <li>
      <Link
        to={`/vehicles/${vehicle.id}`}
        className="flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 transition-colors hover:bg-paper"
      >
        <div className="min-w-0 flex-1 basis-56">
          <p className="truncate font-display text-xl font-semibold">{vehicle.display_name}</p>
          <p className="text-sm text-steel">{vehicleDescription(vehicle)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {role && role !== "owner" && <Badge tone="upcoming">{t(`enums.role.${role}`)}</Badge>}
          {vehicle.status !== "active" && (
            <Badge tone="neutral">{t(`enums.vehicleStatus.${vehicle.status}`)}</Badge>
          )}
          {vehicle.license_plate && <Plate value={vehicle.license_plate} />}
          <span className="w-28 text-end numeric">{format.distance(vehicle.current_mileage)}</span>
          <ChevronRight className="size-4 text-steel rtl:rotate-180" aria-hidden="true" />
        </div>
      </Link>
    </li>
  );
}
