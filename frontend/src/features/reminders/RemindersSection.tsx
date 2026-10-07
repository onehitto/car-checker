import { useTranslation } from "react-i18next";

import { SectionLayout } from "@/features/vehicles/SectionLayout";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";

export function RemindersSection() {
  const { t } = useTranslation();
  const { vehicle } = useVehicleContext();
  const base = `/vehicles/${vehicle.id}/reminders`;
  return (
    <SectionLayout
      label={t("vehicle.tabs.reminders")}
      items={[
        { to: base, label: t("reminders.sections.reminders"), end: true },
        { to: `${base}/notes`, label: t("reminders.sections.notes") },
      ]}
    />
  );
}
