import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "./Button";
import { Dialog, DialogActions } from "./Dialog";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: ReactNode;
  body?: ReactNode;
  confirmLabel?: ReactNode;
  onConfirm: () => void;
  pending?: boolean;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  body,
  confirmLabel,
  onConfirm,
  pending,
}: ConfirmDialogProps) {
  const { t } = useTranslation();
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title={title ?? t("common.confirmDeleteTitle")}>
      <p className="text-steel">{body ?? t("common.confirmDeleteBody")}</p>
      <DialogActions>
        <Button variant="secondary" onClick={() => onOpenChange(false)}>
          {t("common.cancel")}
        </Button>
        <Button variant="danger" onClick={onConfirm} loading={pending}>
          {confirmLabel ?? t("common.delete")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
