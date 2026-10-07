import type { ComponentProps, ReactNode } from "react";

import { Select } from "./Field";

/** Filters on the left, actions on the right; wraps on phones. */
export function Toolbar({ children, actions }: { children?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-3">
      {children}
      {actions && <div className="ms-auto flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

/** Select whose label is only read by assistive technologies (the options speak for it). */
export function FilterSelect({
  label,
  ...props
}: ComponentProps<typeof Select> & { label: string }) {
  return (
    <label>
      <span className="sr-only">{label}</span>
      <Select className="w-auto min-w-40" {...props} />
    </label>
  );
}
