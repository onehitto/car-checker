import { useTranslation } from "react-i18next";

import type { Tire } from "@/api/types";
import { Dialog, ErrorState, LoadingState, LogList, LogRow } from "@/components/ui";
import { useFormat } from "@/lib/useFormat";

import { useTireEvents } from "./queries";

export function TireHistoryDialog({
  vehicleId,
  tire,
  onClose,
}: {
  vehicleId: string;
  tire: Tire;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const format = useFormat();
  const events = useTireEvents(vehicleId, tire.id);
  return (
    <Dialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={t("tires.historyTitle", { name: `${tire.brand} ${tire.size}` })}
      size="lg"
    >
      {events.isPending ? (
        <LoadingState />
      ) : events.isError ? (
        <ErrorState error={events.error} onRetry={() => void events.refetch()} />
      ) : events.data.items.length === 0 ? (
        <p className="text-steel">{t("tires.noHistory")}</p>
      ) : (
        <LogList>
          {events.data.items.map((event) => (
            <LogRow
              key={event.id}
              date={format.date(event.event_date)}
              mileage={event.mileage === null ? "" : format.distance(event.mileage)}
              title={t(`enums.tireEvent.${event.event_type}`)}
              details={[
                event.from_position && event.to_position
                  ? t("tires.moved", {
                      from: t(`enums.tirePosition.${event.from_position}`),
                      to: t(`enums.tirePosition.${event.to_position}`),
                    })
                  : event.to_position
                    ? t(`enums.tirePosition.${event.to_position}`)
                    : null,
                event.tread_depth_mm
                  ? t("tires.treadValue", { value: event.tread_depth_mm })
                  : null,
                event.notes,
              ]
                .filter(Boolean)
                .join(", ")}
            />
          ))}
        </LogList>
      )}
    </Dialog>
  );
}
