import { Plus, Search } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, expectNoContent } from "@/api/client";
import { EXPENSE_CATEGORIES } from "@/api/enums";
import type { Expense } from "@/api/types";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  FilterSelect,
  Input,
  LoadingState,
  LogList,
  LogRow,
  Pagination,
  Panel,
  RowMenu,
  Toolbar,
} from "@/components/ui";
import { useVehicleContext } from "@/features/vehicles/vehicleContext";
import { useConfirmDelete } from "@/lib/useConfirmDelete";
import { useFormat } from "@/lib/useFormat";
import { useSearchFilters } from "@/lib/useSearchFilters";

import { ExpenseFormDialog } from "./ExpenseFormDialog";
import { type ExpenseFilters, useExpenses } from "./queries";

/** Every cost of the vehicle: typed by hand or coming from services, parts and fill-ups. */
export function ExpensesTab() {
  const { t } = useTranslation();
  const format = useFormat();
  const { vehicle, canEdit } = useVehicleContext();
  const { values, page, update, setPage } = useSearchFilters({ category: "", q: "" });
  const search = useDeferredValue(values.q);
  const expenses = useExpenses(vehicle.id, {
    page,
    category: values.category
      ? ([values.category] as NonNullable<ExpenseFilters["category"]>)
      : undefined,
    q: search || undefined,
  });
  const [editing, setEditing] = useState<Expense | "new" | null>(null);
  const remove = useConfirmDelete(
    (expense: Expense) =>
      expectNoContent(
        api.DELETE("/api/v1/vehicles/{vehicle_id}/expenses/{expense_id}", {
          params: { path: { vehicle_id: vehicle.id, expense_id: expense.id } },
        }),
      ),
    { successMessage: t("expenses.deleted") },
  );
  const filtered = values.category !== "" || values.q !== "";

  return (
    <>
      <Toolbar
        actions={
          canEdit && (
            <Button icon={<Plus className="size-4" />} onClick={() => setEditing("new")}>
              {t("expenses.add")}
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
            placeholder={t("expenses.searchPlaceholder")}
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
          {EXPENSE_CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {t(`enums.expenseCategory.${category}`)}
            </option>
          ))}
        </FilterSelect>
      </Toolbar>

      <Panel bodyClassName="py-1">
        {expenses.isPending ? (
          <LoadingState />
        ) : expenses.isError ? (
          <ErrorState error={expenses.error} onRetry={() => void expenses.refetch()} />
        ) : expenses.data.items.length === 0 ? (
          <EmptyState
            title={filtered ? t("expenses.noMatch") : t("expenses.emptyTitle")}
            body={filtered ? undefined : t("expenses.emptyBody")}
          />
        ) : (
          <LogList>
            {expenses.data.items.map((expense) => {
              const manual = expense.source === "manual";
              return (
                <LogRow
                  key={expense.id}
                  date={format.date(expense.expense_date)}
                  mileage={expense.mileage === null ? "" : format.distance(expense.mileage)}
                  title={expense.title}
                  details={
                    <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      <span>{t(`enums.expenseCategory.${expense.category}`)}</span>
                      {expense.vendor && <span>{expense.vendor}</span>}
                      {!manual && (
                        <Badge tone="neutral">{t(`expenses.source.${expense.source}`)}</Badge>
                      )}
                    </span>
                  }
                  amount={format.money(expense.amount, expense.currency)}
                  actions={
                    canEdit &&
                    manual && (
                      <RowMenu
                        label={t("common.moreActions")}
                        actions={[
                          { label: t("common.edit"), onSelect: () => setEditing(expense) },
                          {
                            label: t("common.delete"),
                            danger: true,
                            onSelect: () => remove.ask(expense),
                          },
                        ]}
                      />
                    )
                  }
                />
              );
            })}
          </LogList>
        )}
      </Panel>
      {expenses.data && (
        <Pagination
          page={expenses.data.meta.page}
          totalPages={expenses.data.meta.total_pages}
          total={expenses.data.meta.total}
          onPageChange={setPage}
        />
      )}
      {editing && (
        <ExpenseFormDialog
          vehicle={vehicle}
          expense={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {remove.dialog}
    </>
  );
}
