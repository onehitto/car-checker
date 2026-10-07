import { useTranslation } from "react-i18next";

import { SectionLayout } from "@/features/vehicles/SectionLayout";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";

export function CostsSection() {
  const { t } = useTranslation();
  const { vehicle } = useVehicleContext();
  const base = `/vehicles/${vehicle.id}/expenses`;
  return (
    <SectionLayout
      label={t("vehicle.tabs.costs")}
      items={[
        { to: base, label: t("expenses.sections.expenses"), end: true },
        { to: `${base}/statistics`, label: t("expenses.sections.statistics") },
      ]}
    />
  );
}
