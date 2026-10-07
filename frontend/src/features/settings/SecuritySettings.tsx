import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, expectNoContent, unwrap } from "@/api/client";
import { session } from "@/api/session";
import type { SessionInfo } from "@/api/types";
import {
  Badge,
  Button,
  errorMessage,
  ErrorState,
  Field,
  FormAlert,
  Input,
  ItemRow,
  LoadingState,
  Panel,
  useToast,
} from "@/components/ui";
import { passwordSchema } from "@/features/auth/schemas";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { useFormat } from "@/lib/useFormat";
import { describeUserAgent } from "@/lib/userAgent";
import { field } from "@/lib/validation";

export function SecuritySettings() {
  return (
    <div className="grid max-w-5xl items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <ChangePassword />
      <Sessions />
    </div>
  );
}

function ChangePassword() {
  const { t } = useTranslation();
  const schema = useMemo(
    () =>
      z
        .object({
          current_password: field.text(128),
          new_password: passwordSchema(t),
          confirm: z.string(),
        })
        .refine((values) => values.new_password === values.confirm, {
          path: ["confirm"],
          error: t("auth.passwordsDiffer"),
        }),
    [t],
  );
  const form = useZodForm(schema, { current_password: "", new_password: "", confirm: "" });
  const errors = form.formState.errors;
  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    ({ current_password, new_password }) =>
      expectNoContent(
        api.POST("/api/v1/auth/password/change", { body: { current_password, new_password } }),
      ),
    {
      successMessage: t("settings.security.passwordChanged"),
      onSuccess: () => form.reset(),
    },
  );
  return (
    <Panel title={t("settings.security.passwordTitle")}>
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
        {formError && <FormAlert>{formError}</FormAlert>}
        <p className="text-sm text-steel">{t("settings.security.passwordBody")}</p>
        <Field label={t("settings.security.current")} error={errors.current_password?.message}>
          {(props) => (
            <Input
              type="password"
              autoComplete="current-password"
              {...props}
              {...form.register("current_password")}
            />
          )}
        </Field>
        <Field
          label={t("auth.newPassword")}
          hint={t("auth.passwordRule")}
          error={errors.new_password?.message}
        >
          {(props) => (
            <Input
              type="password"
              autoComplete="new-password"
              {...props}
              {...form.register("new_password")}
            />
          )}
        </Field>
        <Field label={t("auth.confirmPassword")} error={errors.confirm?.message}>
          {(props) => (
            <Input
              type="password"
              autoComplete="new-password"
              {...props}
              {...form.register("confirm")}
            />
          )}
        </Field>
        <div>
          <Button type="submit" loading={pending}>
            {t("settings.security.changePassword")}
          </Button>
        </div>
      </form>
    </Panel>
  );
}

function Sessions() {
  const { t } = useTranslation();
  const toast = useToast();
  const format = useFormat();
  const sessions = useQuery({
    queryKey: ["me", "sessions"],
    queryFn: () => unwrap(api.GET("/api/v1/users/me/sessions")),
  });
  const revoke = useConfirmDelete(
    (item: SessionInfo) =>
      expectNoContent(
        api.DELETE("/api/v1/users/me/sessions/{session_id}", {
          params: { path: { session_id: item.id } },
        }),
      ),
    {
      successMessage: t("settings.security.revoked"),
      title: t("settings.security.revokeTitle"),
      body: t("settings.security.revokeBody"),
    },
  );
  const signOutEverywhere = useMutation({
    mutationFn: () => expectNoContent(api.POST("/api/v1/auth/logout-all")),
    meta: { invalidate: false },
    onSuccess: () => session.clear(),
    onError: (error) => toast.error(errorMessage(error, t)),
  });

  return (
    <Panel
      title={t("settings.security.sessionsTitle")}
      actions={
        <Button
          variant="secondary"
          size="sm"
          loading={signOutEverywhere.isPending}
          onClick={() => signOutEverywhere.mutate()}
        >
          {t("settings.security.signOutEverywhere")}
        </Button>
      }
      bodyClassName="py-1"
    >
      {sessions.isPending ? (
        <LoadingState />
      ) : sessions.isError ? (
        <ErrorState error={sessions.error} onRetry={() => void sessions.refetch()} />
      ) : (
        <ul className="divide-y divide-rule">
          {sessions.data.map((item) => {
            const agent = describeUserAgent(item.user_agent);
            const browser =
              agent.browser === "API client" ? t("settings.security.apiClient") : agent.browser;
            const { os } = agent;
            const device =
              browser && os
                ? t("settings.security.device", { browser, os })
                : browser || os || t("settings.security.unknownDevice");
            return (
              <ItemRow
                key={item.id}
                title={
                  <span className="flex flex-wrap items-center gap-2">
                    {device}
                    {item.current && <Badge tone="ok">{t("settings.security.thisDevice")}</Badge>}
                  </span>
                }
                details={[
                  t("settings.security.lastUsed", { date: format.dateTime(item.last_used_at) }),
                  item.ip_address,
                ]
                  .filter(Boolean)
                  .join(", ")}
                aside={
                  !item.current && (
                    <Button variant="ghost" size="sm" onClick={() => revoke.ask(item)}>
                      {t("settings.security.revoke")}
                    </Button>
                  )
                }
              />
            );
          })}
        </ul>
      )}
      {revoke.dialog}
    </Panel>
  );
}
