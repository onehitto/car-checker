import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { CONSUMPTION_UNITS } from "@/api/enums";
import { Button, Field, FieldRow, FormAlert, Input, Panel, Select } from "@/components/ui";
import { useCurrentUser } from "@/features/auth/authContext";
import { ME_QUERY_KEY } from "@/features/auth/meQuery";
import { useVehicleList } from "@/features/vehicles/queries";
import { i18n, LANGUAGES } from "@/i18n";
import { CURRENCIES } from "@/lib/currencies";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { asInput, field } from "@/lib/validation";

import { VehicleCurrencyDialog } from "./VehicleCurrencyDialog";

const PHONE = /^\+?[0-9 ().-]{6,32}$/;

const schema = z.object({
  first_name: field.text(100),
  last_name: field.text(100),
  phone_number: field.optionalText(32).pipe(
    z
      .string()
      .regex(PHONE, { error: () => i18n.t("garages.fields.phoneInvalid") })
      .nullable(),
  ),
  preferred_language: field.choice(LANGUAGES),
  preferred_currency: z.string().length(3),
  preferred_distance_unit: field.choice(["km", "mi"]),
  preferred_consumption_unit: field.choice(CONSUMPTION_UNITS),
  timezone: field.text(64),
});

function timeZones(current: string): string[] {
  try {
    const zones = Intl.supportedValuesOf("timeZone");
    return zones.includes(current) ? zones : [current, ...zones];
  } catch {
    return [current];
  }
}

export function ProfileSettings() {
  const { t } = useTranslation();
  const user = useCurrentUser();
  const queryClient = useQueryClient();
  const form = useZodForm(schema, {
    first_name: user.first_name,
    last_name: user.last_name,
    phone_number: asInput(user.phone_number),
    preferred_language: user.preferred_language,
    preferred_currency: user.preferred_currency,
    preferred_distance_unit: user.preferred_distance_unit,
    preferred_consumption_unit: user.preferred_consumption_unit,
    timezone: user.timezone,
  });
  const errors = form.formState.errors;
  const vehicles = useVehicleList({ limit: 100, sort: "created_at" });
  // Vehicles the user owns that are in another currency than the profile's.
  const otherCurrency = (vehicles.data?.items ?? []).filter(
    (vehicle) =>
      (vehicle.access_role ?? "owner") === "owner" && vehicle.currency !== user.preferred_currency,
  );
  const [offerCurrency, setOfferCurrency] = useState(false);
  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    (body) => unwrap(api.PATCH("/api/v1/users/me", { body })),
    {
      successMessage: t("settings.profile.saved"),
      onSuccess: (updated) => {
        queryClient.setQueryData(ME_QUERY_KEY, updated);
        if (updated.preferred_currency !== user.preferred_currency) setOfferCurrency(true);
      },
    },
  );

  const currencies = CURRENCIES.includes(user.preferred_currency as (typeof CURRENCIES)[number])
    ? [...CURRENCIES]
    : [user.preferred_currency, ...CURRENCIES];

  return (
    <form noValidate onSubmit={onSubmit} className="flex max-w-3xl flex-col gap-6">
      {formError && <FormAlert>{formError}</FormAlert>}
      <Panel title={t("settings.profile.you")} bodyClassName="flex flex-col gap-4">
        <FieldRow>
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
        </FieldRow>
        <FieldRow>
          <Field label={t("auth.email")} hint={t("settings.profile.emailHint")}>
            {(props) => <Input value={user.email} readOnly disabled {...props} />}
          </Field>
          <Field label={t("garages.fields.phone")} optional error={errors.phone_number?.message}>
            {(props) => (
              <Input
                type="tel"
                dir="ltr"
                autoComplete="tel"
                {...props}
                {...form.register("phone_number")}
              />
            )}
          </Field>
        </FieldRow>
      </Panel>
      <Panel title={t("settings.profile.preferences")} bodyClassName="flex flex-col gap-4">
        <FieldRow>
          <Field
            label={t("common.language")}
            hint={t("settings.profile.languageHint")}
            error={errors.preferred_language?.message}
          >
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
          <Field
            label={t("settings.profile.timezone")}
            hint={t("settings.profile.timezoneHint")}
            error={errors.timezone?.message}
          >
            {(props) => (
              <Select {...props} {...form.register("timezone")}>
                {timeZones(user.timezone).map((zone) => (
                  <option key={zone} value={zone}>
                    {zone.replaceAll("_", " ")}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        </FieldRow>
        <FieldRow columns={3}>
          <Field
            label={t("auth.currency")}
            hint={t("settings.profile.currencyHint")}
            error={errors.preferred_currency?.message}
          >
            {(props) => (
              <Select {...props} {...form.register("preferred_currency")}>
                {currencies.map((code) => (
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
          <Field
            label={t("settings.profile.consumption")}
            error={errors.preferred_consumption_unit?.message}
          >
            {(props) => (
              <Select {...props} {...form.register("preferred_consumption_unit")}>
                {CONSUMPTION_UNITS.map((unit) => (
                  <option key={unit} value={unit}>
                    {t(`units.consumption.${unit}`)}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        </FieldRow>
        {otherCurrency.length > 0 && (
          <p className="text-sm text-steel">
            {t("settings.profile.otherCurrency", {
              count: otherCurrency.length,
              currency: user.preferred_currency,
            })}{" "}
            <button
              type="button"
              className="font-medium text-petrol hover:underline"
              onClick={() => setOfferCurrency(true)}
            >
              {t("settings.profile.useForVehicles", { currency: user.preferred_currency })}
            </button>
          </p>
        )}
      </Panel>
      <div>
        <Button type="submit" loading={pending}>
          {t("common.saveChanges")}
        </Button>
      </div>
      {offerCurrency && otherCurrency.length > 0 && (
        <VehicleCurrencyDialog
          currency={user.preferred_currency}
          vehicles={otherCurrency}
          onClose={() => setOfferCurrency(false)}
        />
      )}
    </form>
  );
}
