import type { ReactNode } from "react";

/** Error about the whole form (field errors are shown next to their inputs). */
export function FormAlert({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="rounded-md bg-overdue-soft px-3 py-2 text-sm text-overdue">
      {children}
    </p>
  );
}
