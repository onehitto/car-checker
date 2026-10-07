import type { Vehicle } from "@/api/types";

/** "Dacia Logan Stepway, 2019" */
export function vehicleDescription(vehicle: Vehicle): string {
  const name = [vehicle.brand, vehicle.model, vehicle.trim].filter(Boolean).join(" ");
  return `${name}, ${vehicle.year}`;
}
