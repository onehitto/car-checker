import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, unwrap } from "@/api/client";
import { TIRE_POSITIONS } from "@/api/enums";
import type { Tire, Vehicle } from "@/api/types";
import {
  errorMessage,
  Field,
  FieldRow,
  FormDialog,
  Input,
  Select,
  useToast,
} from "@/components/ui";
import { todayIso } from "@/lib/format";
import { useFormat } from "@/lib/useFormat";

type Position = (typeof TIRE_POSITIONS)[number];

/** Swap mounted tires (e.g. front to rear) in one go; positions must stay unique. */
export function RotationDialog({
  vehicle,
  mounted,
  onClose,
}: {
  vehicle: Vehicle;
  mounted: Tire[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const format = useFormat();
  const [positions, setPositions] = useState<Record<string, Position>>(() =>
    Object.fromEntries(mounted.map((tire) => [tire.id, tire.position as Position])),
  );
  const [date, setDate] = useState(todayIso());
  const [mileage, setMileage] = useState(String(format.toUnit(vehicle.current_mileage)));
  const [error, setError] = useState<string | null>(null);

  const chosen = Object.values(positions);
  const duplicate = chosen.length !== new Set(chosen).size;
  const moves = mounted
    .filter((tire) => positions[tire.id] !== tire.position)
    .map((tire) => ({ tire_id: tire.id, to_position: positions[tire.id]! }));

  const rotate = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/api/v1/vehicles/{vehicle_id}/tires/rotations", {
          params: { path: { vehicle_id: vehicle.id } },
          body: {
            rotation_date: date,
            mileage: mileage.trim() === "" ? null : format.toKm(Number(mileage)),
            moves,
          },
        }),
      ),
    onSuccess: () => {
      toast.success(t("tires.rotated"));
      onClose();
    },
    onError: (failure) => setError(errorMessage(failure, t)),
  });

  return (
    <FormDialog
      title={t("tires.rotateTitle")}
      description={t("tires.rotateBody")}
      submitLabel={t("tires.rotate")}
      onSubmit={(event) => {
        event.preventDefault();
        if (duplicate) setError(t("tires.duplicatePositions"));
        else if (moves.length === 0) setError(t("tires.nothingMoved"));
        else {
          setError(null);
          rotate.mutate();
        }
      }}
      onClose={onClose}
      pending={rotate.isPending}
      error={error}
    >
      <ul className="flex flex-col gap-3">
        {mounted.map((tire) => (
          <li
            key={tire.id}
            className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_12rem] sm:items-center"
          >
            <span>
              <span className="font-medium">
                {tire.brand} {tire.size}
              </span>
              <span className="block text-sm text-steel">
                {t("tires.now", { position: t(`enums.tirePosition.${tire.position as Position}`) })}
              </span>
            </span>
            <label>
              <span className="sr-only">{t("tires.moveTo")}</span>
              <Select
                value={positions[tire.id]}
                onChange={(event) =>
                  setPositions((current) => ({
                    ...current,
                    [tire.id]: event.target.value as Position,
                  }))
                }
              >
                {TIRE_POSITIONS.map((position) => (
                  <option key={position} value={position}>
                    {t(`enums.tirePosition.${position}`)}
                  </option>
                ))}
              </Select>
            </label>
          </li>
        ))}
      </ul>
      <FieldRow>
        <Field label={t("common.date")}>
          {(props) => (
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} {...props} />
          )}
        </Field>
        <Field label={t("common.mileageIn", { unit: format.unitLabel })} optional>
          {(props) => (
            <Input
              inputMode="numeric"
              value={mileage}
              onChange={(e) => setMileage(e.target.value)}
              {...props}
            />
          )}
        </Field>
      </FieldRow>
    </FormDialog>
  );
}
