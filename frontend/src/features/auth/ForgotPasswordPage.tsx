import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { Button, errorMessage, Field, FormAlert, Input } from "@/components/ui";

import { emailSchema } from "./schemas";

export function ForgotPasswordPage() {
  const { t } = useTranslation();
  const schema = useMemo(() => z.object({ email: emailSchema(t) }), [t]);
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { email: "" },
  });
  const request = useMutation({
    mutationFn: (values: z.infer<typeof schema>) =>
      unwrap(api.POST("/api/v1/auth/password/forgot", { body: values })),
  });

  if (request.isSuccess) {
    return (
      <>
        <h1 className="text-4xl">{t("auth.checkInboxTitle")}</h1>
        <p className="mt-3 text-steel">
          {t("auth.checkInboxBody", { email: form.getValues("email") })}
        </p>
        <Link to="/login" className="mt-8 font-medium text-petrol hover:underline">
          {t("auth.backToSignIn")}
        </Link>
      </>
    );
  }

  return (
    <>
      <h1 className="text-4xl">{t("auth.forgotTitle")}</h1>
      <p className="mt-2 text-steel">{t("auth.forgotBody")}</p>
      <form
        className="mt-8 flex flex-col gap-4"
        noValidate
        onSubmit={form.handleSubmit((values) => request.mutate(values))}
      >
        {request.isError && <FormAlert>{errorMessage(request.error, t)}</FormAlert>}
        <Field label={t("auth.email")} error={form.formState.errors.email?.message}>
          {(props) => (
            <Input type="email" autoComplete="email" {...props} {...form.register("email")} />
          )}
        </Field>
        <Button type="submit" loading={request.isPending}>
          {t("auth.sendResetLink")}
        </Button>
      </form>
      <Link to="/login" className="mt-6 text-sm font-medium text-petrol hover:underline">
        {t("auth.backToSignIn")}
      </Link>
    </>
  );
}
