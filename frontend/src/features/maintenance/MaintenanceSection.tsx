import { useTranslation } from "react-i18next";

import { SectionLayout } from "@/features/vehicles/SectionLayout";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";

export function MaintenanceSection() {
  const { t } = useTranslation();
  const { vehicle } = useVehicleContext();
  const base = `/vehicles/${vehicle.id}/maintenance`;
  return (
    <SectionLayout
      label={t("vehicle.tabs.maintenance")}
      items={[
        { to: base, label: t("maintenance.sections.history"), end: true },
        { to: `${base}/schedules`, label: t("maintenance.sections.schedules") },
        { to: `${base}/oil-changes`, label: t("maintenance.sections.oil") },
        { to: `${base}/parts`, label: t("maintenance.sections.parts") },
        { to: `${base}/tires`, label: t("maintenance.sections.tires") },
      ]}
    />
  );
}
