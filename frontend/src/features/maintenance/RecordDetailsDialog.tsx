import { useTranslation } from "react-i18next";

import type { MaintenanceRecord, Vehicle } from "@/api/types";
import { Dialog, DetailList } from "@/components/ui";
import { useFormat } from "@/lib/useFormat";

export function RecordDetailsDialog({
  vehicle,
  record,
  onClose,
}: {
  vehicle: Vehicle;
  record: MaintenanceRecord;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const format = useFormat();
  const currency = vehicle.currency;
  return (
    <Dialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={record.title}
      description={`${format.date(record.service_date)}${
        record.mileage === null ? "" : `, ${format.distance(record.mileage)}`
      }`}
      size="lg"
    >
      <DetailList
        items={[
          { label: t("maintenance.fields.type"), value: record.maintenance_type.name },
          { label: t("maintenance.fields.kind"), value: t(`enums.maintenanceKind.${record.kind}`) },
          { label: t("maintenance.fields.garage"), value: record.garage?.name },
          { label: t("common.total"), value: format.money(record.cost, currency) },
          {
            label: t("maintenance.fields.labor"),
            value: format.money(record.labor_cost, currency),
          },
          {
            label: t("maintenance.fields.parts"),
            value: format.money(record.parts_cost, currency),
          },
        ]}
      />
      {record.description && (
        <section className="mt-5">
          <h3 className="text-sm font-medium text-steel">{t("maintenance.fields.workDone")}</h3>
          <p className="whitespace-pre-line">{record.description}</p>
        </section>
      )}
      {record.notes && (
        <section className="mt-4">
          <h3 className="text-sm font-medium text-steel">{t("common.notes")}</h3>
          <p className="whitespace-pre-line">{record.notes}</p>
        </section>
      )}
    </Dialog>
  );
}
