import * as RadixDialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  size?: "md" | "lg";
}

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  size = "md",
}: DialogProps) {
  const { t } = useTranslation();
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-40 bg-ink/50" />
        <RadixDialog.Content
          className={cn(
            "fixed inset-x-3 top-[5vh] z-50 mx-auto max-h-[90vh] overflow-y-auto rounded-panel bg-sheet shadow-xl focus:outline-none",
            size === "md" ? "max-w-lg" : "max-w-2xl",
          )}
        >
          <div className="flex items-start justify-between gap-4 border-b border-rule px-5 py-4">
            <div>
              <RadixDialog.Title className="font-display text-2xl font-semibold leading-tight">
                {title}
              </RadixDialog.Title>
              {description ? (
                <RadixDialog.Description className="mt-1 text-sm text-steel">
                  {description}
                </RadixDialog.Description>
              ) : (
                <RadixDialog.Description className="sr-only">{title}</RadixDialog.Description>
              )}
            </div>
            <RadixDialog.Close
              className="rounded-md p-1 text-steel hover:bg-paper hover:text-ink"
              aria-label={t("common.close")}
            >
              <X className="size-5" />
            </RadixDialog.Close>
          </div>
          <div className="px-5 py-4">{children}</div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}

/** Footer row for forms inside a dialog. */
export function DialogActions({ children }: { children: ReactNode }) {
  return <div className="mt-6 flex flex-wrap justify-end gap-2">{children}</div>;
}
