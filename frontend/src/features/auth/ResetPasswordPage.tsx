import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router";
import { z } from "zod";

import { api, expectNoContent } from "@/api/client";
import { Button, Field, Input, useToast } from "@/components/ui";
import { applyServerErrors } from "@/lib/forms";

import { passwordSchema } from "./schemas";

export function ResetPasswordPage() {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [formError, setFormError] = useState<string | null>(null);

  const schema = useMemo(
    () =>
      z
        .object({ new_password: passwordSchema(t), confirm: z.string() })
        .refine((values) => values.new_password === values.confirm, {
          path: ["confirm"],
          message: t("auth.passwordsDiffer"),
        }),
    [t],
  );
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { new_password: "", confirm: "" },
  });
  const reset = useMutation({
    mutationFn: (values: z.infer<typeof schema>) =>
      expectNoContent(
        api.POST("/api/v1/auth/password/reset", {
          body: { token, new_password: values.new_password },
        }),
      ),
    onSuccess: () => {
      toast.success(t("auth.passwordReset"));
      void navigate("/login", { replace: true });
    },
    onError: (error) => setFormError(applyServerErrors(error, form.setError, ["new_password"], t)),
  });

  if (!token) {
    return (
      <>
        <h1 className="text-4xl">{t("auth.resetTitle")}</h1>
        <p className="mt-3 text-overdue">{t("auth.resetLinkInvalid")}</p>
        <Link to="/forgot-password" className="mt-6 font-medium text-petrol hover:underline">
          {t("auth.sendResetLink")}
        </Link>
      </>
    );
  }

  return (
    <>
      <h1 className="text-4xl">{t("auth.resetTitle")}</h1>
      <p className="mt-2 text-steel">{t("auth.resetBody")}</p>
      <form
        className="mt-8 flex flex-col gap-4"
        noValidate
        onSubmit={form.handleSubmit((values) => {
          setFormError(null);
          reset.mutate(values);
        })}
      >
        {formError && (
          <p role="alert" className="rounded-md bg-overdue-soft px-3 py-2 text-sm text-overdue">
            {formError}
          </p>
        )}
        <Field
          label={t("auth.newPassword")}
          error={form.formState.errors.new_password?.message}
          hint={t("auth.passwordRule")}
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
        <Field label={t("auth.confirmPassword")} error={form.formState.errors.confirm?.message}>
          {(props) => (
            <Input
              type="password"
              autoComplete="new-password"
              {...props}
              {...form.register("confirm")}
            />
          )}
        </Field>
        <Button type="submit" loading={reset.isPending}>
          {t("auth.setPassword")}
        </Button>
      </form>
    </>
  );
}
