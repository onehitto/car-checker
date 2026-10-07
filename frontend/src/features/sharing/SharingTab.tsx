import { useMutation, useQuery } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, expectNoContent, unwrap } from "@/api/client";
import { isApiError } from "@/api/errors";
import { SHARED_ROLES } from "@/api/enums";
import type { Share } from "@/api/types";
import {
  Button,
  EmptyState,
  errorMessage,
  ErrorState,
  Field,
  FormAlert,
  Input,
  LoadingState,
  Panel,
  Select,
  useToast,
} from "@/components/ui";
import { vehicleKeys } from "@/features/vehicles/queries";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { field } from "@/lib/validation";

const schema = z.object({ email: field.email(), role: field.choice(SHARED_ROLES) });

/** Owner only: give a family member or a mechanic access to this vehicle. */
export function SharingTab() {
  const { t } = useTranslation();
  const toast = useToast();
  const { vehicle, isOwner } = useVehicleContext();
  const shares = useQuery({
    queryKey: vehicleKeys.part(vehicle.id, "access"),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/vehicles/{vehicle_id}/access", {
          params: { path: { vehicle_id: vehicle.id } },
        }),
      ),
    enabled: isOwner,
  });

  const form = useZodForm(schema, { email: "", role: "viewer" });
  const errors = form.formState.errors;
  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (body) =>
      unwrap(
        api.POST("/api/v1/vehicles/{vehicle_id}/access", {
          params: { path: { vehicle_id: vehicle.id } },
          body,
        }),
      ).catch((error: unknown) => {
        // "No account uses this e-mail" belongs next to the e-mail field.
        if (isApiError(error) && error.code === "NOT_FOUND") {
          form.setError("email", { type: "server", message: t("sharing.noAccount") });
          return null;
        }
        throw error;
      }),
    {
      onSuccess: (share) => {
        if (!share) return;
        toast.success(t("sharing.shared", { name: share.user.first_name }));
        form.reset({ email: "", role: "viewer" });
      },
    },
  );

  const changeRole = useMutation({
    mutationFn: ({ share, role }: { share: Share; role: Share["role"] }) =>
      unwrap(
        api.PATCH("/api/v1/vehicles/{vehicle_id}/access/{access_id}", {
          params: { path: { vehicle_id: vehicle.id, access_id: share.id } },
          body: { role },
        }),
      ),
    onSuccess: () => toast.success(t("sharing.roleChanged")),
    onError: (error) => toast.error(errorMessage(error, t)),
  });
  const revoke = useConfirmDelete(
    (share: Share) =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/access/{access_id}", {
          params: { path: { vehicle_id: vehicle.id, access_id: share.id } },
        }),
      ),
    {
      successMessage: t("sharing.revoked"),
      title: t("sharing.revokeTitle"),
      body: t("sharing.revokeBody"),
    },
  );

  if (!isOwner) return <EmptyState title={t("errors.forbidden")} />;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
      <Panel title={t("sharing.people")} bodyClassName="py-1">
        {shares.isPending ? (
          <LoadingState />
        ) : shares.isError ? (
          <ErrorState error={shares.error} onRetry={() => void shares.refetch()} />
        ) : shares.data.length === 0 ? (
          <EmptyState title={t("sharing.emptyTitle")} body={t("sharing.emptyBody")} />
        ) : (
          <ul className="divide-y divide-rule">
            {shares.data.map((share) => (
              <li key={share.id} className="flex flex-wrap items-center gap-3 py-3">
                <div className="min-w-0 flex-1 basis-48">
                  <p className="font-medium">
                    {share.user.first_name} {share.user.last_name}
                  </p>
                  <p className="truncate text-sm text-steel">{share.user.email}</p>
                </div>
                <label>
                  <span className="sr-only">{t("sharing.role")}</span>
                  <Select
                    className="w-auto"
                    value={share.role}
                    disabled={changeRole.isPending}
                    onChange={(event) =>
                      changeRole.mutate({ share, role: event.target.value as Share["role"] })
                    }
                  >
                    {SHARED_ROLES.map((role) => (
                      <option key={role} value={role}>
                        {t(`enums.role.${role}`)}
                      </option>
                    ))}
                  </Select>
                </label>
                <Button variant="ghost" size="sm" onClick={() => revoke.ask(share)}>
                  {t("sharing.revoke")}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title={t("sharing.invite")}>
        <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
          {formError && <FormAlert>{formError}</FormAlert>}
          <Field
            label={t("auth.email")}
            hint={t("sharing.emailHint")}
            error={errors.email?.message}
          >
            {(props) => <Input type="email" {...props} {...form.register("email")} />}
          </Field>
          <Field label={t("sharing.role")} error={errors.role?.message}>
            {(props) => (
              <Select {...props} {...form.register("role")}>
                {SHARED_ROLES.map((role) => (
                  <option key={role} value={role}>
                    {t(`enums.role.${role}`)}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <ul className="flex flex-col gap-1 text-sm text-steel">
            <li>{t("sharing.editorExplained")}</li>
            <li>{t("sharing.viewerExplained")}</li>
          </ul>
          <Button type="submit" loading={pending} icon={<UserPlus className="size-4" />}>
            {t("sharing.share")}
          </Button>
        </form>
      </Panel>
      {revoke.dialog}
    </div>
  );
}
