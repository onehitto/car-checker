import { useTranslation } from "react-i18next";

import { SectionLayout } from "@/features/vehicles/SectionLayout";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";

export function DocumentsSection() {
  const { t } = useTranslation();
  const { vehicle } = useVehicleContext();
  const base = `/vehicles/${vehicle.id}/documents`;
  return (
    <SectionLayout
      label={t("vehicle.tabs.documents")}
      items={[
        { to: base, label: t("documents.sections.documents"), end: true },
        { to: `${base}/files`, label: t("documents.sections.files") },
      ]}
    />
  );
}
