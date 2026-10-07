import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { api, expectNoContent } from "@/api/client";
import type { Vehicle } from "@/api/types";
import { Button, ConfirmDialog, errorMessage, Panel, useToast } from "@/components/ui";

import { vehicleKeys } from "./queries";

export function VehicleDangerZone({ vehicle }: { vehicle: Vehicle }) {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);

  const remove = useMutation({
    mutationFn: () =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}", {
          params: { path: { vehicle_id: vehicle.id } },
        }),
      ),
    // Leave the page before refreshing, or its queries would refetch a deleted vehicle.
    meta: { invalidate: false },
    onSuccess: async () => {
      await navigate("/vehicles", { replace: true });
      queryClient.removeQueries({ queryKey: vehicleKeys.detail(vehicle.id) });
      await queryClient.invalidateQueries();
      toast.success(t("vehicles.deleted", { name: vehicle.display_name }));
    },
    onError: (error) => toast.error(errorMessage(error, t)),
  });

  return (
    <Panel title={t("vehicles.delete.title")} bodyClassName="flex flex-col items-start gap-3">
      <p className="text-sm text-steel">{t("vehicles.delete.body")}</p>
      <Button variant="danger" size="sm" onClick={() => setConfirming(true)}>
        {t("vehicles.delete.action")}
      </Button>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={t("vehicles.delete.confirmTitle", { name: vehicle.display_name })}
        body={t("vehicles.delete.confirmBody")}
        confirmLabel={t("vehicles.delete.action")}
        pending={remove.isPending}
        onConfirm={() => remove.mutate()}
      />
    </Panel>
  );
}
