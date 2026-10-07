import { ArrowLeft } from "lucide-react";
import { useWatch } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import { z } from "zod";

import { api, unwrap } from "@/api/client";
import { FUEL_TYPES, TRANSMISSIONS, VEHICLE_STATUSES } from "@/api/enums";
import type { Vehicle } from "@/api/types";
import {
  Button,
  ErrorState,
  Field,
  FieldRow,
  FormAlert,
  Input,
  LoadingState,
  PageHeader,
  Panel,
  Select,
  Textarea,
} from "@/components/ui";
import { useCurrentUser } from "@/features/auth/authContext";
import { CURRENCIES } from "@/lib/currencies";
import { useFormSubmit, useZodForm } from "@/lib/forms";
import { useFormat } from "@/lib/useFormat";
import { asInput, field } from "@/lib/validation";

import { useVehicle } from "./queries";
import { VehicleDangerZone } from "./VehicleDangerZone";
import { VehiclePhotoPanel } from "./VehiclePhotoPanel";
import { vehicleContextFor } from "./vehicleContext";

const schema = z.object({
  brand: field.text(64),
  model: field.text(64),
  year: field.int(1886, 2100),
  trim: field.optionalText(64),
  nickname: field.optionalText(100),
  license_plate: field.optionalText(20),
  vin: field.optionalText(17),
  color: field.optionalText(32),
  fuel_type: field.choice(FUEL_TYPES),
  transmission_type: field.optionalChoice(TRANSMISSIONS),
  engine: field.optionalText(64),
  engine_displacement_cc: field.optionalPositiveInt(20_000),
  horsepower: field.optionalPositiveInt(3_000),
  initial_mileage: field.int(0, 2_000_000),
  current_mileage: field.optionalInt(0, 2_000_000),
  purchase_date: field.optionalDate(),
  purchase_price: field.optionalDecimal(),
  currency: z.string().length(3),
  status: field.choice(VEHICLE_STATUSES),
  notes: field.optionalText(10_000),
});
type Input = z.input<typeof schema>;

/** /vehicles/new and /vehicles/:vehicleId/edit */
export function VehicleFormPage() {
  const { vehicleId } = useParams();
  if (!vehicleId) return <VehicleForm />;
  return <EditVehicle vehicleId={vehicleId} key={vehicleId} />;
}

function EditVehicle({ vehicleId }: { vehicleId: string }) {
  const vehicle = useVehicle(vehicleId);
  if (vehicle.isPending) return <LoadingState />;
  if (vehicle.isError)
    return <ErrorState error={vehicle.error} onRetry={() => void vehicle.refetch()} />;
  return <VehicleForm vehicle={vehicle.data} />;
}

function VehicleForm({ vehicle }: { vehicle?: Vehicle }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useCurrentUser();
  const format = useFormat();
  const editing = vehicle !== undefined;
  const isOwner = vehicle ? vehicleContextFor(vehicle).isOwner : true;

  const form = useZodForm(schema, {
    brand: vehicle?.brand ?? "",
    model: vehicle?.model ?? "",
    year: asInput(vehicle?.year),
    trim: asInput(vehicle?.trim),
    nickname: asInput(vehicle?.nickname),
    license_plate: asInput(vehicle?.license_plate),
    vin: asInput(vehicle?.vin),
    color: asInput(vehicle?.color),
    fuel_type: vehicle?.fuel_type ?? "petrol",
    transmission_type: vehicle?.transmission_type ?? "",
    engine: asInput(vehicle?.engine),
    engine_displacement_cc: asInput(vehicle?.engine_displacement_cc),
    horsepower: asInput(vehicle?.horsepower),
    initial_mileage: vehicle ? String(format.toUnit(vehicle.initial_mileage)) : "0",
    current_mileage: "",
    purchase_date: asInput(vehicle?.purchase_date),
    purchase_price: asInput(vehicle?.purchase_price),
    currency: vehicle?.currency ?? user.preferred_currency,
    status: vehicle?.status ?? "active",
    notes: asInput(vehicle?.notes),
  } satisfies Input);
  const errors = form.formState.errors;
  const currency = useWatch({ control: form.control, name: "currency" });

  const { onSubmit, pending, formError } = useFormSubmit(
    form,
    ({ current_mileage, initial_mileage, ...values }) => {
      const body = { ...values, initial_mileage: format.toKm(initial_mileage) };
      if (vehicle) {
        return unwrap(
          api.PATCH("/api/v1/vehicles/{vehicle_id}", {
            params: { path: { vehicle_id: vehicle.id } },
            body,
          }),
        );
      }
      return unwrap(
        api.POST("/api/v1/vehicles", {
          body: {
            ...body,
            current_mileage: current_mileage === null ? null : format.toKm(current_mileage),
          },
        }),
      );
    },
    {
      successMessage: editing ? t("vehicles.saved") : t("vehicles.added"),
      onSuccess: (saved) => void navigate(`/vehicles/${saved.id}`),
    },
  );

  const unit = format.unitLabel;
  const backTo = vehicle ? `/vehicles/${vehicle.id}` : "/vehicles";

  return (
    <>
      <Link
        to={backTo}
        className="mb-3 inline-flex items-center gap-1.5 text-sm text-steel hover:text-ink"
      >
        <ArrowLeft className="size-4 rtl:rotate-180" aria-hidden="true" />
        {vehicle ? vehicle.display_name : t("vehicles.title")}
      </Link>
      <PageHeader
        title={editing ? t("vehicles.editTitle") : t("vehicles.addTitle")}
        description={editing ? undefined : t("vehicles.addBody")}
      />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <form noValidate onSubmit={onSubmit} className="flex flex-col gap-6">
          {formError && <FormAlert>{formError}</FormAlert>}

          <Panel title={t("vehicles.sections.identity")} bodyClassName="flex flex-col gap-4">
            <FieldRow columns={3}>
              <Field label={t("vehicles.fields.brand")} error={errors.brand?.message}>
                {(props) => <Input placeholder="Dacia" {...props} {...form.register("brand")} />}
              </Field>
              <Field label={t("vehicles.fields.model")} error={errors.model?.message}>
                {(props) => <Input placeholder="Logan" {...props} {...form.register("model")} />}
              </Field>
              <Field label={t("vehicles.fields.year")} error={errors.year?.message}>
                {(props) => <Input inputMode="numeric" {...props} {...form.register("year")} />}
              </Field>
            </FieldRow>
            <FieldRow>
              <Field label={t("vehicles.fields.trim")} optional error={errors.trim?.message}>
                {(props) => <Input {...props} {...form.register("trim")} />}
              </Field>
              <Field
                label={t("vehicles.fields.nickname")}
                optional
                hint={t("vehicles.fields.nicknameHint")}
                error={errors.nickname?.message}
              >
                {(props) => <Input {...props} {...form.register("nickname")} />}
              </Field>
            </FieldRow>
            <FieldRow columns={3}>
              <Field
                label={t("vehicles.fields.licensePlate")}
                optional
                error={errors.license_plate?.message}
              >
                {(props) => (
                  <Input
                    dir="ltr"
                    autoCapitalize="characters"
                    {...props}
                    {...form.register("license_plate")}
                  />
                )}
              </Field>
              <Field label={t("vehicles.fields.vin")} optional error={errors.vin?.message}>
                {(props) => (
                  <Input
                    dir="ltr"
                    autoCapitalize="characters"
                    {...props}
                    {...form.register("vin")}
                  />
                )}
              </Field>
              <Field label={t("vehicles.fields.color")} optional error={errors.color?.message}>
                {(props) => <Input {...props} {...form.register("color")} />}
              </Field>
            </FieldRow>
          </Panel>

          <Panel title={t("vehicles.sections.engine")} bodyClassName="flex flex-col gap-4">
            <FieldRow>
              <Field label={t("vehicles.fields.fuelType")} error={errors.fuel_type?.message}>
                {(props) => (
                  <Select {...props} {...form.register("fuel_type")}>
                    {FUEL_TYPES.map((value) => (
                      <option key={value} value={value}>
                        {t(`enums.fuelType.${value}`)}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
              <Field
                label={t("vehicles.fields.transmission")}
                optional
                error={errors.transmission_type?.message}
              >
                {(props) => (
                  <Select {...props} {...form.register("transmission_type")}>
                    <option value="">{t("common.notSet")}</option>
                    {TRANSMISSIONS.map((value) => (
                      <option key={value} value={value}>
                        {t(`enums.transmission.${value}`)}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            </FieldRow>
            <FieldRow columns={3}>
              <Field label={t("vehicles.fields.engine")} optional error={errors.engine?.message}>
                {(props) => <Input placeholder="1.5 dCi" {...props} {...form.register("engine")} />}
              </Field>
              <Field
                label={t("vehicles.fields.displacement")}
                optional
                error={errors.engine_displacement_cc?.message}
              >
                {(props) => (
                  <Input
                    inputMode="numeric"
                    {...props}
                    {...form.register("engine_displacement_cc")}
                  />
                )}
              </Field>
              <Field
                label={t("vehicles.fields.horsepower")}
                optional
                error={errors.horsepower?.message}
              >
                {(props) => (
                  <Input inputMode="numeric" {...props} {...form.register("horsepower")} />
                )}
              </Field>
            </FieldRow>
          </Panel>

          <Panel title={t("vehicles.sections.odometer")} bodyClassName="flex flex-col gap-4">
            <FieldRow>
              <Field
                label={t("vehicles.fields.initialMileage", { unit })}
                hint={t("vehicles.fields.initialMileageHint")}
                error={errors.initial_mileage?.message}
              >
                {(props) => (
                  <Input inputMode="numeric" {...props} {...form.register("initial_mileage")} />
                )}
              </Field>
              {!editing && (
                <Field
                  label={t("vehicles.fields.currentMileage", { unit })}
                  optional
                  hint={t("vehicles.fields.currentMileageHint")}
                  error={errors.current_mileage?.message}
                >
                  {(props) => (
                    <Input inputMode="numeric" {...props} {...form.register("current_mileage")} />
                  )}
                </Field>
              )}
            </FieldRow>
          </Panel>

          <Panel title={t("vehicles.sections.purchase")} bodyClassName="flex flex-col gap-4">
            <FieldRow columns={3}>
              <Field
                label={t("vehicles.fields.purchaseDate")}
                optional
                error={errors.purchase_date?.message}
              >
                {(props) => <Input type="date" {...props} {...form.register("purchase_date")} />}
              </Field>
              <Field
                label={t("vehicles.fields.purchasePrice")}
                optional
                error={errors.purchase_price?.message}
              >
                {(props) => (
                  <Input inputMode="decimal" {...props} {...form.register("purchase_price")} />
                )}
              </Field>
              <Field
                label={t("auth.currency")}
                hint={
                  vehicle && currency !== vehicle.currency
                    ? t("vehicles.fields.currencyChangeHint")
                    : t("vehicles.fields.currencyHint")
                }
                error={errors.currency?.message}
              >
                {(props) => (
                  <Select {...props} {...form.register("currency")}>
                    {currencyOptions(vehicle?.currency ?? user.preferred_currency).map((code) => (
                      <option key={code} value={code}>
                        {code}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            </FieldRow>
            {editing && (
              <Field
                label={t("vehicles.status")}
                hint={t("vehicles.fields.statusHint")}
                error={errors.status?.message}
                className="sm:max-w-xs"
              >
                {(props) => (
                  <Select {...props} {...form.register("status")}>
                    {VEHICLE_STATUSES.map((value) => (
                      <option key={value} value={value}>
                        {t(`enums.vehicleStatus.${value}`)}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            )}
            <Field label={t("common.notes")} optional error={errors.notes?.message}>
              {(props) => <Textarea {...props} {...form.register("notes")} />}
            </Field>
          </Panel>

          <div className="flex flex-wrap gap-2">
            <Button type="submit" loading={pending}>
              {editing ? t("common.saveChanges") : t("nav.addVehicle")}
            </Button>
            <Button variant="secondary" onClick={() => void navigate(backTo)}>
              {t("common.cancel")}
            </Button>
          </div>
        </form>

        {vehicle && (
          <aside className="flex flex-col gap-6">
            <VehiclePhotoPanel vehicle={vehicle} />
            {isOwner && <VehicleDangerZone vehicle={vehicle} />}
          </aside>
        )}
      </div>
    </>
  );
}

function currencyOptions(current: string): string[] {
  return CURRENCIES.includes(current as (typeof CURRENCIES)[number])
    ? [...CURRENCIES]
    : [current, ...CURRENCIES];
}
