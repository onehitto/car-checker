import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api, unwrap } from "@/api/client";
import type { Vehicle } from "@/api/types";
import { Button, Dialog, DialogActions, errorMessage, FormAlert, useToast } from "@/components/ui";

/**
 * The profile currency is only the default for new vehicles: offer to switch the user's
 * existing vehicles too. Amounts are relabelled, not converted.
 */
export function VehicleCurrencyDialog({
  currency,
  vehicles,
  onClose,
}: {
  currency: string;
  vehicles: Vehicle[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const apply = useMutation({
    mutationFn: async () => {
      for (const vehicle of vehicles) {
        await unwrap(
          api.PATCH("/api/v1/vehicles/{vehicle_id}", {
            params: { path: { vehicle_id: vehicle.id } },
            body: { currency },
          }),
        );
      }
    },
    onSuccess: () => {
      toast.success(t("settings.currency.done", { count: vehicles.length, currency }));
      onClose();
    },
  });

  return (
    <Dialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={t("settings.currency.title", { currency })}
      description={t("settings.currency.body")}
    >
      {apply.isError && <FormAlert>{errorMessage(apply.error, t)}</FormAlert>}
      <ul className="mt-2 flex flex-col divide-y divide-rule">
        {vehicles.map((vehicle) => (
          <li key={vehicle.id} className="flex items-center justify-between gap-3 py-2">
            <span>{vehicle.display_name}</span>
            <span className="text-sm text-steel">
              {vehicle.currency} → {currency}
            </span>
          </li>
        ))}
      </ul>
      <DialogActions>
        <Button variant="secondary" onClick={onClose}>
          {t("settings.currency.keep")}
        </Button>
        <Button loading={apply.isPending} onClick={() => apply.mutate()}>
          {t("settings.currency.apply", { currency })}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
