import { useTranslation } from "react-i18next";

import { SectionLayout } from "@/features/vehicles/SectionLayout";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";

export function MileageSection() {
  const { t } = useTranslation();
  const { vehicle } = useVehicleContext();
  const base = `/vehicles/${vehicle.id}/mileage`;
  return (
    <SectionLayout
      label={t("vehicle.tabs.mileage")}
      items={[
        { to: base, label: t("mileage.sections.readings"), end: true },
        { to: `${base}/fuel`, label: t("mileage.sections.fuel") },
      ]}
    />
  );
}
