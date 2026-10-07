import { CircleAlert, CircleCheck, X } from "lucide-react";
import { type ReactNode, useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

import { ToastContext, type ToastApi } from "./toastContext";

type ToastKind = "success" | "error";

interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
}

const DURATION_MS = 5000;
let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const push = useCallback(
    (kind: ToastKind, message: string) => {
      const id = nextId++;
      setToasts((current) => [...current.slice(-2), { id, kind, message }]);
      window.setTimeout(() => dismiss(id), DURATION_MS);
    },
    [dismiss],
  );

  const api = useMemo<ToastApi>(
    () => ({
      success: (message) => push("success", message),
      error: (message) => push("error", message),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-3 bottom-4 z-50 flex flex-col items-end gap-2 sm:inset-x-auto sm:end-4"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role={toast.kind === "error" ? "alert" : "status"}
            className={cn(
              "pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-panel border bg-sheet px-4 py-3 shadow-lg",
              toast.kind === "error" ? "border-overdue/40" : "border-rule",
            )}
          >
            {toast.kind === "error" ? (
              <CircleAlert className="mt-0.5 size-5 shrink-0 text-overdue" aria-hidden="true" />
            ) : (
              <CircleCheck className="mt-0.5 size-5 shrink-0 text-ok" aria-hidden="true" />
            )}
            <p className="flex-1 text-sm">{toast.message}</p>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="text-steel hover:text-ink"
              aria-label={t("common.close")}
            >
              <X className="size-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
