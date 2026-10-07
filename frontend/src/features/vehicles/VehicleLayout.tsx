import { Gauge, Pencil } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Outlet, useParams } from "react-router";

import {
  Badge,
  Button,
  ButtonLink,
  ErrorState,
  LoadingState,
  Odometer,
  Plate,
  type TabItem,
  TabNav,
} from "@/components/ui";
import { useAttachmentUrl } from "@/features/attachments/useAttachmentUrl";
import { MileageDialog } from "@/features/mileage/MileageDialog";
import { useFormat } from "@/lib/useFormat";

import { vehicleDescription } from "./describe";
import { useVehicle } from "./queries";
import { vehicleContextFor } from "./vehicleContext";

/** /vehicles/:vehicleId — header band (name, plate, odometer) and one tab per area. */
export function VehicleLayout() {
  const { vehicleId = "" } = useParams();
  const vehicle = useVehicle(vehicleId);
  if (vehicle.isPending) return <LoadingState />;
  if (vehicle.isError)
    return <ErrorState error={vehicle.error} onRetry={() => void vehicle.refetch()} />;
  return <VehiclePage key={vehicleId} context={vehicleContextFor(vehicle.data)} />;
}

function VehiclePage({ context }: { context: ReturnType<typeof vehicleContextFor> }) {
  const { t } = useTranslation();
  const format = useFormat();
  const { vehicle, canEdit } = context;
  const [updatingMileage, setUpdatingMileage] = useState(false);
  const photo = useAttachmentUrl(vehicle.id, vehicle.image_attachment_id);
  const base = `/vehicles/${vehicle.id}`;
  const role = vehicle.access_role;

  const tabs: TabItem[] = [
    { to: base, label: t("vehicle.tabs.overview"), end: true },
    { to: `${base}/maintenance`, label: t("vehicle.tabs.maintenance") },
    { to: `${base}/mileage`, label: t("vehicle.tabs.mileage") },
    { to: `${base}/expenses`, label: t("vehicle.tabs.costs") },
    { to: `${base}/documents`, label: t("vehicle.tabs.documents") },
  ];

  return (
    <>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-x-8 gap-y-5">
        <div className="flex min-w-0 items-center gap-4">
          {photo.data && (
            <img
              src={photo.data}
              alt=""
              className="size-16 shrink-0 rounded-md object-cover sm:size-20"
            />
          )}
          <div className="min-w-0">
            <h1 className="text-3xl leading-tight sm:text-4xl">{vehicle.display_name}</h1>
            <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-steel">
              <span>{vehicleDescription(vehicle)}</span>
              <span>{t(`enums.fuelType.${vehicle.fuel_type}`)}</span>
              {vehicle.license_plate && <Plate value={vehicle.license_plate} />}
              {role && role !== "owner" && <Badge tone="upcoming">{t(`enums.role.${role}`)}</Badge>}
              {vehicle.status !== "active" && (
                <Badge tone="neutral">{t(`enums.vehicleStatus.${vehicle.status}`)}</Badge>
              )}
            </div>
          </div>
        </div>
        <div className="flex flex-col items-start gap-3 sm:items-end">
          <Odometer
            value={format.toUnit(vehicle.current_mileage)}
            unit={format.unit}
            label={t("vehicle.odometer", { distance: format.distance(vehicle.current_mileage) })}
          />
          {canEdit && (
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="secondary"
                icon={<Gauge className="size-4" />}
                onClick={() => setUpdatingMileage(true)}
              >
                {t("mileage.update")}
              </Button>
              <ButtonLink
                to={`${base}/edit`}
                size="sm"
                variant="ghost"
                icon={<Pencil className="size-4" />}
              >
                {t("vehicle.edit")}
              </ButtonLink>
            </div>
          )}
        </div>
      </header>

      <TabNav label={t("vehicle.tabsLabel")} items={tabs} />
      <div className="mt-6">
        <Outlet context={context} />
      </div>

      {updatingMileage && (
        <MileageDialog vehicle={vehicle} onClose={() => setUpdatingMileage(false)} />
      )}
    </>
  );
}
