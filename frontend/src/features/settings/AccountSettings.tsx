import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, expectNoContent } from "@/api/client";
import { session } from "@/api/session";
import { Button, Field, FormDialog, Input, Panel } from "@/components/ui";
import { useCurrentUser } from "@/features/auth/authContext";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { field } from "@/lib/validation";

export function AccountSettings() {
  const { t } = useTranslation();
  const user = useCurrentUser();
  const [deleting, setDeleting] = useState(false);
  return (
    <Panel
      title={t("settings.account.deleteTitle")}
      className="max-w-3xl"
      bodyClassName="flex flex-col items-start gap-3"
    >
      <p className="max-w-prose text-steel">
        {t("settings.account.deleteBody", { email: user.email })}
      </p>
      <Button variant="danger" onClick={() => setDeleting(true)}>
        {t("settings.account.delete")}
      </Button>
      {deleting && <DeleteAccountDialog onClose={() => setDeleting(false)} />}
    </Panel>
  );
}

const schema = z.object({ password: field.text(128) });

function DeleteAccountDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const form = useZodForm(schema, { password: "" });
  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (body) => expectNoContent(api.DELETE("/api/v1/users/me", { body })),
    {
      invalidate: false,
      onSuccess: () => {
        queryClient.clear();
        session.clear();
      },
    },
  );
  return (
    <FormDialog
      title={t("settings.account.confirmTitle")}
      description={t("settings.account.confirmBody")}
      submitLabel={t("settings.account.delete")}
      onSubmit={onSubmit}
      onClose={onClose}
      pending={pending}
      error={formError}
    >
      <Field label={t("auth.password")} error={form.formState.errors.password?.message}>
        {(props) => (
          <Input
            type="password"
            autoComplete="current-password"
            {...props}
            {...form.register("password")}
          />
        )}
      </Field>
    </FormDialog>
  );
}
