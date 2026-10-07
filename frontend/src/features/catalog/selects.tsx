import { type ComponentProps, useMemo } from "react";
import { useTranslation } from "react-i18next";

import { Select } from "@/components/ui";

import { useGarageOptions, useMaintenanceTypes, usePartTypes } from "./queries";

type SelectProps = ComponentProps<typeof Select>;

interface TypeOption {
  id: string;
  name: string;
  category: string;
}

function groupByCategory<T extends TypeOption>(types: T[]): [string, T[]][] {
  const groups = new Map<string, T[]>();
  for (const type of types) groups.set(type.category, [...(groups.get(type.category) ?? []), type]);
  return [...groups.entries()];
}

// The selects are registered with react-hook-form (uncontrolled). Remounting them once the
// options arrive lets the form write its current value into the new element.

/** Maintenance types grouped by category. `exclude` hides types (e.g. already scheduled). */
export function MaintenanceTypeSelect({
  exclude = [],
  placeholder,
  ...props
}: SelectProps & { exclude?: string[]; placeholder?: string }) {
  const { t } = useTranslation();
  const types = useMaintenanceTypes();
  const groups = useMemo(
    () => groupByCategory((types.data ?? []).filter((type) => !exclude.includes(type.id))),
    [types.data, exclude],
  );
  return (
    <Select key={types.isSuccess ? "ready" : "loading"} {...props}>
      <option value="">{placeholder ?? t("catalog.chooseType")}</option>
      {groups.map(([category, items]) => (
        <optgroup
          key={category}
          label={t(`enums.maintenanceCategory.${category}` as "enums.maintenanceCategory.other")}
        >
          {items.map((type) => (
            <option key={type.id} value={type.id}>
              {type.name}
            </option>
          ))}
        </optgroup>
      ))}
    </Select>
  );
}

export function PartTypeSelect(props: SelectProps) {
  const { t } = useTranslation();
  const types = usePartTypes();
  const groups = useMemo(() => groupByCategory(types.data ?? []), [types.data]);
  return (
    <Select key={types.isSuccess ? "ready" : "loading"} {...props}>
      <option value="">{t("catalog.chooseType")}</option>
      {groups.map(([category, items]) => (
        <optgroup
          key={category}
          label={t(`enums.partCategory.${category}` as "enums.partCategory.other")}
        >
          {items.map((type) => (
            <option key={type.id} value={type.id}>
              {type.name}
            </option>
          ))}
        </optgroup>
      ))}
    </Select>
  );
}

export function GarageSelect(props: SelectProps) {
  const { t } = useTranslation();
  const garages = useGarageOptions();
  return (
    <Select key={garages.isSuccess ? "ready" : "loading"} {...props}>
      <option value="">{t("common.notSet")}</option>
      {garages.data?.map((garage) => (
        <option key={garage.id} value={garage.id}>
          {garage.city ? `${garage.name} (${garage.city})` : garage.name}
        </option>
      ))}
    </Select>
  );
}
