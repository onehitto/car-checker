import { useMutation } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";

import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { errorMessage } from "@/components/ui/errorMessage";
import { useToast } from "@/components/ui/toastContext";

interface ConfirmDeleteOptions {
  successMessage: string;
  title?: ReactNode;
  body?: ReactNode;
}

/** Ask before deleting: `ask(item)` opens the confirmation, render `dialog` once. */
export function useConfirmDelete<T>(
  remove: (item: T) => Promise<unknown>,
  { successMessage, title, body }: ConfirmDeleteOptions,
) {
  const { t } = useTranslation();
  const toast = useToast();
  const [target, setTarget] = useState<T | null>(null);
  const mutation = useMutation({
    mutationFn: remove,
    onSuccess: () => {
      toast.success(successMessage);
      setTarget(null);
    },
    onError: (error) => toast.error(errorMessage(error, t)),
  });
  const dialog = (
    <ConfirmDialog
      open={target !== null}
      onOpenChange={(open) => !open && setTarget(null)}
      title={title}
      body={body}
      pending={mutation.isPending}
      onConfirm={() => target !== null && mutation.mutate(target)}
    />
  );
  return { ask: setTarget, dialog };
}
