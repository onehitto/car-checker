import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useSearchParams } from "react-router";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { Button, errorMessage, Field, Input } from "@/components/ui";

import { useAuth } from "./authContext";
import { emailSchema } from "./schemas";

export function LoginPage() {
  const { t } = useTranslation();
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [formError, setFormError] = useState<string | null>(null);

  const schema = useMemo(
    () => z.object({ email: emailSchema(t), password: z.string().min(1, t("errors.required")) }),
    [t],
  );
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  const login = useMutation({
    mutationFn: (values: z.infer<typeof schema>) =>
      unwrap(api.POST("/api/v1/auth/login", { body: values })),
    onSuccess: (result) => {
      signIn(result);
      const next = params.get("next");
      void navigate(next?.startsWith("/") ? next : "/", { replace: true });
    },
    onError: (error) => setFormError(errorMessage(error, t)),
  });

  return (
    <>
      <h1 className="text-4xl">{t("auth.signInTitle")}</h1>
      <p className="mt-2 text-steel">{t("auth.signInBody")}</p>
      <form
        className="mt-8 flex flex-col gap-4"
        noValidate
        onSubmit={form.handleSubmit((values) => {
          setFormError(null);
          login.mutate(values);
        })}
      >
        {formError && (
          <p role="alert" className="rounded-md bg-overdue-soft px-3 py-2 text-sm text-overdue">
            {formError}
          </p>
        )}
        <Field label={t("auth.email")} error={form.formState.errors.email?.message}>
          {(props) => (
            <Input type="email" autoComplete="email" {...props} {...form.register("email")} />
          )}
        </Field>
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
        <div className="-mt-1 text-end text-sm">
          <Link to="/forgot-password" className="text-petrol hover:underline">
            {t("auth.forgotLink")}
          </Link>
        </div>
        <Button type="submit" loading={login.isPending}>
          {t("auth.signIn")}
        </Button>
      </form>
      <p className="mt-6 text-sm text-steel">
        {t("auth.noAccount")}{" "}
        <Link to="/register" className="font-medium text-petrol hover:underline">
          {t("auth.createAccount")}
        </Link>
      </p>
    </>
  );
}
