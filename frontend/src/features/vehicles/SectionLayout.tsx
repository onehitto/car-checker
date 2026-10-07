import { Outlet } from "react-router";

import { type TabItem, TabNav } from "@/components/ui";

import { useVehicleContext } from "./vehicleContext";

/** Sections inside a vehicle tab (e.g. Maintenance: history, schedules, oil changes...). */
export function SectionLayout({ label, items }: { label: string; items: TabItem[] }) {
  const context = useVehicleContext();
  return (
    <div className="flex flex-col gap-5">
      <TabNav variant="secondary" label={label} items={items} />
      <Outlet context={context} />
    </div>
  );
}
