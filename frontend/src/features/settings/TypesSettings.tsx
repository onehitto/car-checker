import { Plus } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent } from "@/api/client";
import type { MaintenanceType, PartType } from "@/api/types";
import { Button, ErrorState, ItemRow, LoadingState, Panel, RowMenu } from "@/components/ui";
import { useMaintenanceTypes, usePartTypes } from "@/features/catalog/queries";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { useFormat } from "@/lib/useFormat";

import { TypeFormDialog } from "./TypeFormDialog";

type Editing =
  { kind: "maintenance"; type?: MaintenanceType } | { kind: "part"; type?: PartType } | null;

/** The user's own maintenance and part types, next to the built-in ones. */
export function TypesSettings() {
  const { t } = useTranslation();
  const format = useFormat();
  const maintenanceTypes = useMaintenanceTypes();
  const partTypes = usePartTypes();
  const [editing, setEditing] = useState<Editing>(null);
  const removeMaintenance = useConfirmDelete(
    (type: MaintenanceType) =>
      expectNoContent(
        api.DELETE("/api/v1/maintenance-types/{type_id}", {
          params: { path: { type_id: type.id } },
        }),
      ),
    { successMessage: t("settings.types.deleted") },
  );
  const removePart = useConfirmDelete(
    (type: PartType) =>
      expectNoContent(
        api.DELETE("/api/v1/part-types/{type_id}", { params: { path: { type_id: type.id } } }),
      ),
    { successMessage: t("settings.types.deleted") },
  );

  const interval = (km: number | null, months: number | null) =>
    [km ? format.distance(km) : null, months ? t("schedules.months", { count: months }) : null]
      .filter(Boolean)
      .join(t("due.or"));

  const sections = [
    {
      kind: "maintenance" as const,
      title: t("settings.types.maintenance"),
      query: maintenanceTypes,
      custom: (maintenanceTypes.data ?? []).filter((type) => !type.is_system),
      builtIn: (maintenanceTypes.data ?? []).filter((type) => type.is_system).length,
    },
    {
      kind: "part" as const,
      title: t("settings.types.parts"),
      query: partTypes,
      custom: (partTypes.data ?? []).filter((type) => !type.is_system),
      builtIn: (partTypes.data ?? []).filter((type) => type.is_system).length,
    },
  ];

  return (
    <div className="grid max-w-5xl gap-6 lg:grid-cols-2">
      {sections.map((section) => (
        <Panel
          key={section.kind}
          title={section.title}
          actions={
            <Button
              size="sm"
              variant="secondary"
              icon={<Plus className="size-4" />}
              onClick={() => setEditing({ kind: section.kind })}
            >
              {t("common.add")}
            </Button>
          }
          bodyClassName="py-1"
        >
          {section.query.isPending ? (
            <LoadingState />
          ) : section.query.isError ? (
            <ErrorState error={section.query.error} onRetry={() => void section.query.refetch()} />
          ) : (
            <>
              <p className="py-3 text-sm text-steel">
                {section.custom.length === 0
                  ? t("settings.types.builtInOnly", { count: section.builtIn })
                  : t("settings.types.builtIn", { count: section.builtIn })}
              </p>
              {section.custom.length > 0 && (
                <ul className="divide-y divide-rule border-t border-rule">
                  {section.custom.map((type) => {
                    const isMaintenance = section.kind === "maintenance";
                    const km = isMaintenance
                      ? (type as MaintenanceType).default_interval_km
                      : (type as PartType).default_lifetime_km;
                    const months = isMaintenance
                      ? (type as MaintenanceType).default_interval_months
                      : (type as PartType).default_lifetime_months;
                    return (
                      <ItemRow
                        key={type.id}
                        title={type.name}
                        details={[
                          isMaintenance
                            ? t(`enums.maintenanceCategory.${(type as MaintenanceType).category}`)
                            : t(`enums.partCategory.${(type as PartType).category}`),
                          interval(km, months),
                        ]
                          .filter(Boolean)
                          .join(", ")}
                        actions={
                          <RowMenu
                            label={t("common.moreActions")}
                            actions={[
                              {
                                label: t("common.edit"),
                                onSelect: () =>
                                  setEditing(
                                    isMaintenance
                                      ? { kind: "maintenance", type: type as MaintenanceType }
                                      : { kind: "part", type: type as PartType },
                                  ),
                              },
                              {
                                label: t("common.delete"),
                                danger: true,
                                onSelect: () =>
                                  isMaintenance
                                    ? removeMaintenance.ask(type as MaintenanceType)
                                    : removePart.ask(type as PartType),
                              },
                            ]}
                          />
                        }
                      />
                    );
                  })}
                </ul>
              )}
            </>
          )}
        </Panel>
      ))}
      {editing?.kind === "maintenance" && (
        <TypeFormDialog kind="maintenance" type={editing.type} onClose={() => setEditing(null)} />
      )}
      {editing?.kind === "part" && (
        <TypeFormDialog kind="part" type={editing.type} onClose={() => setEditing(null)} />
      )}
      {removeMaintenance.dialog}
      {removePart.dialog}
    </div>
  );
}
