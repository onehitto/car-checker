import type { FormEventHandler, ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "./Button";
import { Dialog, DialogActions } from "./Dialog";
import { FormAlert } from "./FormAlert";

interface FormDialogProps {
  title: ReactNode;
  description?: ReactNode;
  submitLabel: ReactNode;
  onSubmit: FormEventHandler<HTMLFormElement>;
  onClose: () => void;
  pending?: boolean;
  error?: string | null;
  size?: "md" | "lg";
  children: ReactNode;
}

/** A form in a dialog. Mount it only while open so each opening starts from fresh values. */
export function FormDialog({
  title,
  description,
  submitLabel,
  onSubmit,
  onClose,
  pending,
  error,
  size,
  children,
}: FormDialogProps) {
  const { t } = useTranslation();
  return (
    <Dialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={title}
      description={description}
      size={size}
    >
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
        {error && <FormAlert>{error}</FormAlert>}
        {children}
        <DialogActions>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" loading={pending}>
            {submitLabel}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}

/** Two or three fields side by side on wide screens. */
export function FieldRow({ children, columns = 2 }: { children: ReactNode; columns?: 2 | 3 }) {
  return (
    <div className={columns === 3 ? "grid gap-4 sm:grid-cols-3" : "grid gap-4 sm:grid-cols-2"}>
      {children}
    </div>
  );
}
