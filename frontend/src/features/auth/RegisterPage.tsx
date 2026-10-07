import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { Button, Field, FormAlert, Input, Select } from "@/components/ui";
import { currentLanguage, LANGUAGES } from "@/i18n";
import { applyServerErrors } from "@/lib/forms";
import { CURRENCIES } from "@/lib/currencies";

import { useAuth } from "./authContext";
import { emailSchema, passwordSchema } from "./schemas";

const FIELDS = [
  "first_name",
  "last_name",
  "email",
  "password",
  "preferred_language",
  "preferred_currency",
  "preferred_distance_unit",
] as const;

function browserTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

export function RegisterPage() {
  const { t } = useTranslation();
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);

  const schema = useMemo(
    () =>
      z.object({
        first_name: z.string().trim().min(1, t("errors.required")).max(100),
        last_name: z.string().trim().min(1, t("errors.required")).max(100),
        email: emailSchema(t),
        password: passwordSchema(t),
        preferred_language: z.enum(LANGUAGES),
        preferred_currency: z.string().length(3),
        preferred_distance_unit: z.enum(["km", "mi"]),
      }),
    [t],
  );
  type Values = z.infer<typeof schema>;
  const language = currentLanguage();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      first_name: "",
      last_name: "",
      email: "",
      password: "",
      preferred_language: language,
      preferred_currency: language === "en" ? "EUR" : language === "fr" ? "EUR" : "MAD",
      preferred_distance_unit: "km",
    },
  });
  const errors = form.formState.errors;

  const register = useMutation({
    mutationFn: (values: Values) =>
      unwrap(
        api.POST("/api/v1/auth/register", { body: { ...values, timezone: browserTimeZone() } }),
      ),
    onSuccess: (result) => {
      signIn(result);
      void navigate("/vehicles/new", { replace: true });
    },
    onError: (error) => setFormError(applyServerErrors(error, form.setError, FIELDS, t)),
  });

  return (
    <>
      <h1 className="text-4xl">{t("auth.registerTitle")}</h1>
      <p className="mt-2 text-steel">{t("auth.registerBody")}</p>
      <form
        className="mt-8 flex flex-col gap-4"
        noValidate
        onSubmit={form.handleSubmit((values) => {
          setFormError(null);
          register.mutate(values);
        })}
      >
        {formError && <FormAlert>{formError}</FormAlert>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("auth.firstName")} error={errors.first_name?.message}>
            {(props) => (
              <Input autoComplete="given-name" {...props} {...form.register("first_name")} />
            )}
          </Field>
          <Field label={t("auth.lastName")} error={errors.last_name?.message}>
            {(props) => (
              <Input autoComplete="family-name" {...props} {...form.register("last_name")} />
            )}
          </Field>
        </div>
        <Field label={t("auth.email")} error={errors.email?.message}>
          {(props) => (
            <Input type="email" autoComplete="email" {...props} {...form.register("email")} />
          )}
        </Field>
        <Field
          label={t("auth.password")}
          error={errors.password?.message}
          hint={t("auth.passwordRule")}
        >
          {(props) => (
            <Input
              type="password"
              autoComplete="new-password"
              {...props}
              {...form.register("password")}
            />
          )}
        </Field>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label={t("common.language")} error={errors.preferred_language?.message}>
            {(props) => (
              <Select {...props} {...form.register("preferred_language")}>
                {LANGUAGES.map((code) => (
                  <option key={code} value={code}>
                    {t(`languages.${code}`)}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field label={t("auth.currency")} error={errors.preferred_currency?.message}>
            {(props) => (
              <Select {...props} {...form.register("preferred_currency")}>
                {CURRENCIES.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field label={t("auth.distanceUnit")} error={errors.preferred_distance_unit?.message}>
            {(props) => (
              <Select {...props} {...form.register("preferred_distance_unit")}>
                <option value="km">{t("units.km")}</option>
                <option value="mi">{t("units.mi")}</option>
              </Select>
            )}
          </Field>
        </div>
        <Button type="submit" loading={register.isPending}>
          {t("auth.createAccount")}
        </Button>
      </form>
      <p className="mt-6 text-sm text-steel">
        {t("auth.haveAccount")}{" "}
        <Link to="/login" className="font-medium text-petrol hover:underline">
          {t("auth.signIn")}
        </Link>
      </p>
    </>
  );
}
