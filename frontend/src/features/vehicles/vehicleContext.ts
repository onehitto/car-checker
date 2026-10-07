import { useOutletContext } from "react-router";

import type { Vehicle } from "@/api/types";

export interface VehicleContextValue {
  vehicle: Vehicle;
  /** Owner or editor: may add and change records. */
  canEdit: boolean;
  isOwner: boolean;
}

export function vehicleContextFor(vehicle: Vehicle): VehicleContextValue {
  const role = vehicle.access_role ?? "owner";
  return { vehicle, canEdit: role !== "viewer", isOwner: role === "owner" };
}

/** The vehicle of the current /vehicles/:vehicleId page. */
export function useVehicleContext(): VehicleContextValue {
  return useOutletContext<VehicleContextValue>();
}
