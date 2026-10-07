import { useInfiniteQuery } from "@tanstack/react-query";
import {
  CircleDot,
  FileText,
  Fuel,
  Gauge,
  Hammer,
  type LucideIcon,
  Receipt,
  Settings2,
  Wrench,
} from "lucide-react";
import { Fragment } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { api, unwrapPage } from "@/api/client";
import { TIMELINE_TYPES } from "@/api/enums";
import type { TimelineEvent } from "@/api/types";
import {
  Button,
  EmptyState,
  ErrorState,
  LoadingState,
  LogList,
  LogRow,
  Panel,
} from "@/components/ui";
import { vehicleKeys } from "@/features/vehicles/queries";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { cn } from "@/lib/cn";
import { useFormat } from "@/lib/useFormat";
import { useSearchFilters } from "@/lib/useSearchFilters";

type EventType = TimelineEvent["type"];

const ICONS: Record<EventType, LucideIcon> = {
  maintenance: Wrench,
  repair: Hammer,
  part: Settings2,
  fuel: Fuel,
  expense: Receipt,
  document: FileText,
  tire: CircleDot,
  mileage: Gauge,
};

/** Where each kind of event is managed, relative to the vehicle page. */
const SECTIONS: Record<EventType, string> = {
  maintenance: "maintenance",
  repair: "maintenance",
  part: "maintenance/parts",
  fuel: "mileage/fuel",
  expense: "expenses",
  document: "documents",
  tire: "maintenance/tires",
  mileage: "mileage",
};

/** The whole life of the vehicle as a logbook, newest first, grouped by year. */
export function TimelineTab() {
  const { t } = useTranslation();
  const format = useFormat();
  const { vehicle } = useVehicleContext();
  const { values, update } = useSearchFilters({ types: "" });
  const selected = values.types ? (values.types.split(",") as EventType[]) : [];

  const events = useInfiniteQuery({
    queryKey: vehicleKeys.part(vehicle.id, "timeline", selected),
    queryFn: ({ pageParam }) =>
      unwrapPage(
        api.GET("/api/v1/vehicles/{vehicle_id}/timeline", {
          params: {
            path: { vehicle_id: vehicle.id },
            query: { type: selected.length ? selected : undefined, page: pageParam, limit: 50 },
          },
        }),
      ),
    initialPageParam: 1,
    getNextPageParam: (last) =>
      last.meta.page < last.meta.total_pages ? last.meta.page + 1 : undefined,
  });

  const toggle = (type: EventType) => {
    const next = selected.includes(type)
      ? selected.filter((item) => item !== type)
      : [...selected, type];
    update({ types: next.join(",") });
  };

  const items = events.data?.pages.flatMap((page) => page.items) ?? [];

  // Readings and fill-ups get a plain-text title from the API ("98910 km", "46.50 L"):
  // format them for the interface language and the user's unit.
  const title = (event: TimelineEvent) => {
    if (event.type === "mileage" && event.mileage !== null) return format.distance(event.mileage);
    const liters = event.type === "fuel" ? /^([\d.]+) L$/.exec(event.title) : null;
    if (liters) return t("oil.liters", { value: format.number(Number(liters[1]), 2) });
    return event.title;
  };

  return (
    <>
      <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label={t("timeline.filter")}>
        {TIMELINE_TYPES.map((type) => {
          const Icon = ICONS[type];
          const active = selected.includes(type);
          return (
            <button
              key={type}
              type="button"
              aria-pressed={active}
              onClick={() => toggle(type)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm transition-colors",
                active
                  ? "border-ink bg-ink text-white"
                  : "border-rule bg-sheet text-steel hover:border-steel hover:text-ink",
              )}
            >
              <Icon className="size-4" aria-hidden="true" />
              {t(`timeline.types.${type}`)}
            </button>
          );
        })}
      </div>
      <Panel bodyClassName="py-1">
        {events.isPending ? (
          <LoadingState />
        ) : events.isError ? (
          <ErrorState error={events.error} onRetry={() => void events.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState title={t("timeline.emptyTitle")} body={t("timeline.emptyBody")} />
        ) : (
          <LogList>
            {items.map((event, index) => {
              const year = event.date.slice(0, 4);
              const newYear = index === 0 || items[index - 1]!.date.slice(0, 4) !== year;
              const Icon = ICONS[event.type];
              return (
                <Fragment key={`${event.type}-${event.id}`}>
                  {newYear && (
                    <li className="pt-5 pb-1">
                      <h2 className="font-display text-2xl font-semibold numeric">{year}</h2>
                    </li>
                  )}
                  <LogRow
                    date={format.date(event.date)}
                    mileage={event.mileage === null ? "" : format.distance(event.mileage)}
                    title={
                      <Link
                        to={`/vehicles/${vehicle.id}/${SECTIONS[event.type]}`}
                        className="inline-flex items-center gap-2 hover:text-petrol"
                      >
                        <Icon className="size-4 shrink-0 text-steel" aria-hidden="true" />
                        {title(event)}
                      </Link>
                    }
                    details={t(`timeline.types.${event.type}`)}
                    amount={event.amount === null ? "" : format.money(event.amount, event.currency)}
                  />
                </Fragment>
              );
            })}
          </LogList>
        )}
      </Panel>
      {events.hasNextPage && (
        <div className="mt-4">
          <Button
            variant="secondary"
            loading={events.isFetchingNextPage}
            onClick={() => void events.fetchNextPage()}
          >
            {t("timeline.loadMore")}
          </Button>
        </div>
      )}
    </>
  );
}
