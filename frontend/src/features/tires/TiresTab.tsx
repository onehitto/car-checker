import { Plus, RefreshCw } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent } from "@/api/client";
import { TIRE_POSITIONS } from "@/api/enums";
import type { Tire } from "@/api/types";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  ItemRow,
  LoadingState,
  Panel,
  RowMenu,
  type Tone,
  Toolbar,
} from "@/components/ui";
import { AttachmentsDialog } from "@/features/attachments/AttachmentsDialog";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { cn } from "@/lib/cn";
import { useConfirmDelete } from "@/lib/useConfirmDelete";

import { useTires } from "./queries";
import { RotationDialog } from "./RotationDialog";
import { TireEventDialog } from "./TireEventDialog";
import { TireFormDialog } from "./TireFormDialog";
import { TireHistoryDialog } from "./TireHistoryDialog";

type Position = (typeof TIRE_POSITIONS)[number];

const STATUS_TONES: Record<Tire["status"], Tone> = {
  mounted: "ok",
  stored: "neutral",
  discarded: "overdue",
};

/** Tires: where each one is mounted, the ones in storage, their history. */
export function TiresTab() {
  const { t } = useTranslation();
  const { vehicle, canEdit } = useVehicleContext();
  const tires = useTires(vehicle.id);
  const [editing, setEditing] = useState<Tire | "new" | null>(null);
  const [logging, setLogging] = useState<Tire | null>(null);
  const [history, setHistory] = useState<Tire | null>(null);
  const [files, setFiles] = useState<Tire | null>(null);
  const [rotating, setRotating] = useState(false);
  const remove = useConfirmDelete(
    (tire: Tire) =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/tires/{tire_id}", {
          params: { path: { vehicle_id: vehicle.id, tire_id: tire.id } },
        }),
      ),
    { successMessage: t("tires.deleted"), body: t("tires.deleteBody") },
  );

  const all = tires.data ?? [];
  const mounted = all.filter((tire) => tire.status === "mounted");
  const byPosition = new Map(mounted.map((tire) => [tire.position, tire]));
  const freePositions = TIRE_POSITIONS.filter((position) => !byPosition.has(position));
  const order = { mounted: 0, stored: 1, discarded: 2 };
  const sorted = [...all].sort(
    (a, b) =>
      order[a.status] - order[b.status] ||
      TIRE_POSITIONS.indexOf((a.position ?? "spare") as Position) -
        TIRE_POSITIONS.indexOf((b.position ?? "spare") as Position),
  );

  const describe = (tire: Tire) =>
    [
      t(`enums.tireSeason.${tire.season}`),
      tire.condition ? t(`enums.tireCondition.${tire.condition}`) : null,
      tire.tread_depth_mm ? t("tires.treadValue", { value: tire.tread_depth_mm }) : null,
      tire.dot_code ? `DOT ${tire.dot_code}` : null,
    ]
      .filter(Boolean)
      .join(", ");

  return (
    <>
      <Toolbar
        actions={
          canEdit && (
            <>
              {mounted.length > 1 && (
                <Button
                  variant="secondary"
                  icon={<RefreshCw className="size-4" />}
                  onClick={() => setRotating(true)}
                >
                  {t("tires.rotate")}
                </Button>
              )}
              <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
                {t("tires.add")}
              </Button>
            </>
          )
        }
      />
      {tires.isPending ? (
        <LoadingState />
      ) : tires.isError ? (
        <ErrorState error={tires.error} onRetry={() => void tires.refetch()} />
      ) : all.length === 0 ? (
        <Panel>
          <EmptyState title={t("tires.emptyTitle")} body={t("tires.emptyBody")} />
        </Panel>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
          <Panel title={t("tires.layout")}>
            <WheelLayout byPosition={byPosition} onSelect={setHistory} />
          </Panel>
          <Panel title={t("tires.all")} bodyClassName="py-1">
            <ul className="divide-y divide-rule">
              {sorted.map((tire) => (
                <ItemRow
                  key={tire.id}
                  title={[tire.brand, tire.model, tire.size].filter(Boolean).join(" ")}
                  details={describe(tire)}
                  aside={
                    <>
                      <Badge tone={STATUS_TONES[tire.status]}>
                        {tire.status === "mounted" && tire.position
                          ? t(`enums.tirePosition.${tire.position}`)
                          : t(`enums.tireStatus.${tire.status}`)}
                      </Badge>
                    </>
                  }
                  actions={
                    <RowMenu
                      label={t("common.moreActions")}
                      actions={[
                        { label: t("tires.history"), onSelect: () => setHistory(tire) },
                        canEdit &&
                          tire.status !== "discarded" && {
                            label: t("tires.log"),
                            onSelect: () => setLogging(tire),
                          },
                        { label: t("files.title"), onSelect: () => setFiles(tire) },
                        canEdit && { label: t("common.edit"), onSelect: () => setEditing(tire) },
                        canEdit && {
                          label: t("common.delete"),
                          danger: true,
                          onSelect: () => remove.ask(tire),
                        },
                      ]}
                    />
                  }
                />
              ))}
            </ul>
          </Panel>
        </div>
      )}

      {editing && (
        <TireFormDialog
          vehicle={vehicle}
          tire={editing === "new" ? undefined : editing}
          freePositions={freePositions}
          onClose={() => setEditing(null)}
        />
      )}
      {logging && (
        <TireEventDialog
          vehicle={vehicle}
          tire={logging}
          freePositions={freePositions}
          onClose={() => setLogging(null)}
        />
      )}
      {history && (
        <TireHistoryDialog vehicleId={vehicle.id} tire={history} onClose={() => setHistory(null)} />
      )}
      {rotating && (
        <RotationDialog vehicle={vehicle} mounted={mounted} onClose={() => setRotating(false)} />
      )}
      {files && (
        <AttachmentsDialog
          vehicleId={vehicle.id}
          entityType="tire"
          entityId={files.id}
          title={t("files.of", { name: `${files.brand} ${files.size}` })}
          canEdit={canEdit}
          onClose={() => setFiles(null)}
        />
      )}
      {remove.dialog}
    </>
  );
}

/** The car seen from above: one slot per wheel and the spare. Drawn left to right (physical). */
function WheelLayout({
  byPosition,
  onSelect,
}: {
  byPosition: Map<string | null, Tire>;
  onSelect: (tire: Tire) => void;
}) {
  const { t } = useTranslation();
  const slot = (position: Position) => {
    const tire = byPosition.get(position);
    const label = t(`enums.tirePosition.${position}`);
    if (!tire) {
      return (
        <div className="flex min-h-20 flex-col justify-center rounded-md border border-dashed border-rule px-2 py-2 text-center text-sm text-steel">
          <span className="font-medium">{label}</span>
          <span>{t("tires.empty")}</span>
        </div>
      );
    }
    return (
      <button
        type="button"
        onClick={() => onSelect(tire)}
        className="flex min-h-20 flex-col justify-center rounded-md border border-rule bg-paper px-2 py-2 text-center text-sm hover:border-petrol"
        aria-label={`${label}: ${tire.brand} ${tire.size}`}
      >
        <span className="text-steel">{label}</span>
        <span className="font-medium">{tire.brand}</span>
        <span className="numeric" dir="ltr">
          {tire.tread_depth_mm ? `${tire.tread_depth_mm} mm` : tire.size}
        </span>
      </button>
    );
  };
  return (
    <div dir="ltr" className="flex flex-col items-center gap-3">
      <span className="text-sm text-steel">{t("tires.front")}</span>
      <div className="grid w-full grid-cols-[1fr_4.5rem_1fr] items-stretch gap-3">
        {slot("front_left")}
        <div
          aria-hidden="true"
          className={cn("row-span-2 rounded-[2rem] border-2 border-ink/80 bg-sheet")}
        />
        {slot("front_right")}
        {slot("rear_left")}
        {slot("rear_right")}
      </div>
      <div className="w-1/2">{slot("spare")}</div>
    </div>
  );
}
