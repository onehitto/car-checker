import { useMutation } from "@tanstack/react-query";
import { Pin, Plus, Search } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent, unwrap } from "@/api/client";
import { NOTE_CATEGORIES } from "@/api/enums";
import type { Note } from "@/api/types";
import {
  Badge,
  Button,
  EmptyState,
  errorMessage,
  ErrorState,
  FilterSelect,
  Input,
  LoadingState,
  Pagination,
  Panel,
  RowMenu,
  Toolbar,
  useToast,
} from "@/components/ui";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { useFormat } from "@/lib/useFormat";
import { useSearchFilters } from "@/lib/useSearchFilters";

import { NoteFormDialog } from "./NoteFormDialog";
import { type NoteFilters, useNotes } from "./queries";

/** Free notes about the vehicle: a noise to watch, a tip from the mechanic... */
export function NotesTab() {
  const { t } = useTranslation();
  const toast = useToast();
  const format = useFormat();
  const { vehicle, canEdit } = useVehicleContext();
  const { values, page, update, setPage } = useSearchFilters({ category: "", q: "" });
  const search = useDeferredValue(values.q);
  const notes = useNotes(vehicle.id, {
    page,
    category: (values.category || undefined) as NoteFilters["category"],
    q: search || undefined,
  });
  const [editing, setEditing] = useState<Note | "new" | null>(null);
  const remove = useConfirmDelete(
    (note: Note) =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/notes/{note_id}", {
          params: { path: { vehicle_id: vehicle.id, note_id: note.id } },
        }),
      ),
    { successMessage: t("notes.deleted") },
  );
  const pin = useMutation({
    mutationFn: (note: Note) =>
      unwrap(
        api.PATCH("/api/v1/vehicles/{vehicle_id}/notes/{note_id}", {
          params: { path: { vehicle_id: vehicle.id, note_id: note.id } },
          body: { is_pinned: !note.is_pinned },
        }),
      ),
    onError: (error) => toast.error(errorMessage(error, t)),
  });
  const filtered = values.category !== "" || values.q !== "";

  return (
    <>
      <Toolbar
        actions={
          canEdit && (
            <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
              {t("notes.add")}
            </Button>
          )
        }
      >
        <label className="relative min-w-48 flex-1 sm:max-w-xs">
          <span className="sr-only">{t("common.search")}</span>
          <Search
            className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-steel"
            aria-hidden="true"
          />
          <Input
            type="search"
            className="ps-9"
            placeholder={t("notes.searchPlaceholder")}
            value={values.q}
            onChange={(event) => update({ q: event.target.value })}
          />
        </label>
        <FilterSelect
          label={t("expenses.fields.category")}
          value={values.category}
          onChange={(event) => update({ category: event.target.value })}
        >
          <option value="">{t("expenses.allCategories")}</option>
          {NOTE_CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {t(`enums.noteCategory.${category}`)}
            </option>
          ))}
        </FilterSelect>
      </Toolbar>
      <Panel bodyClassName="py-1">
        {notes.isPending ? (
          <LoadingState />
        ) : notes.isError ? (
          <ErrorState error={notes.error} onRetry={() => void notes.refetch()} />
        ) : notes.data.items.length === 0 ? (
          <EmptyState
            title={filtered ? t("notes.noMatch") : t("notes.emptyTitle")}
            body={filtered ? undefined : t("notes.emptyBody")}
          />
        ) : (
          <ul className="divide-y divide-rule">
            {notes.data.items.map((note) => (
              <li key={note.id} className="flex gap-3 py-4">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    {note.is_pinned && (
                      <Pin className="size-4 text-petrol" aria-label={t("notes.pinned")} />
                    )}
                    {note.title && (
                      <h3 className="font-sans text-base font-semibold">{note.title}</h3>
                    )}
                    <Badge tone="neutral">{t(`enums.noteCategory.${note.category}`)}</Badge>
                    <span className="text-sm text-steel numeric">
                      {format.date(note.updated_at)}
                    </span>
                  </div>
                  <p className="mt-1 max-w-prose whitespace-pre-line">{note.body}</p>
                </div>
                {canEdit && (
                  <div className="w-8 shrink-0">
                    <RowMenu
                      label={t("common.moreActions")}
                      actions={[
                        {
                          label: note.is_pinned ? t("notes.unpin") : t("notes.pin"),
                          onSelect: () => pin.mutate(note),
                        },
                        { label: t("common.edit"), onSelect: () => setEditing(note) },
                        {
                          label: t("common.delete"),
                          danger: true,
                          onSelect: () => remove.ask(note),
                        },
                      ]}
                    />
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Panel>
      {notes.data && (
        <Pagination
          page={notes.data.meta.page}
          totalPages={notes.data.meta.total_pages}
          total={notes.data.meta.total}
          onPageChange={setPage}
        />
      )}
      {editing && (
        <NoteFormDialog
          vehicle={vehicle}
          note={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {remove.dialog}
    </>
  );
}
