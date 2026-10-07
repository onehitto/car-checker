import { type ComponentProps, type ReactNode, useId } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

const CONTROL =
  "w-full rounded-md border border-rule bg-sheet px-3 text-ink placeholder:text-steel/70 " +
  "focus:border-petrol focus:ring-2 focus:ring-petrol/20 focus:outline-none " +
  "aria-[invalid=true]:border-overdue disabled:bg-paper disabled:text-steel";

interface FieldProps {
  label: ReactNode;
  error?: string;
  hint?: ReactNode;
  optional?: boolean;
  className?: string;
  children: (props: {
    id: string;
    "aria-invalid": boolean;
    "aria-describedby"?: string;
  }) => ReactNode;
}

/** Label + control + hint/error, wired for accessibility. */
export function Field({ label, error, hint, optional, className, children }: FieldProps) {
  const { t } = useTranslation();
  const id = useId();
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
        {optional && <span className="ms-1 font-normal text-steel">({t("common.optional")})</span>}
      </label>
      {children({ id, "aria-invalid": Boolean(error), "aria-describedby": describedBy })}
      {error ? (
        <p id={`${id}-error`} className="text-sm text-overdue">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-sm text-steel">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function Input({ className, ...props }: ComponentProps<"input">) {
  return <input className={cn(CONTROL, "h-10", className)} {...props} />;
}

export function Textarea({ className, rows = 3, ...props }: ComponentProps<"textarea">) {
  return <textarea rows={rows} className={cn(CONTROL, "py-2", className)} {...props} />;
}

export function Select({ className, children, ...props }: ComponentProps<"select">) {
  return (
    <select className={cn(CONTROL, "h-10 pe-8", className)} {...props}>
      {children}
    </select>
  );
}

export function Checkbox({
  label,
  className,
  ...props
}: ComponentProps<"input"> & { label: ReactNode }) {
  return (
    <label className={cn("inline-flex items-center gap-2 text-sm", className)}>
      <input type="checkbox" className="size-4 rounded border-rule accent-petrol" {...props} />
      {label}
    </label>
  );
}
