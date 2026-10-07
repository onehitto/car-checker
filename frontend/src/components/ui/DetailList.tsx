import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export interface Detail {
  label: ReactNode;
  value: ReactNode;
}

/** Label / value pairs; empty values show a dash. */
export function DetailList({ items, className }: { items: Detail[]; className?: string }) {
  return (
    <dl className={cn("grid gap-x-6 gap-y-3 sm:grid-cols-2", className)}>
      {items.map((item, index) => (
        <div key={index} className="flex flex-col">
          <dt className="text-sm text-steel">{item.label}</dt>
          <dd className="numeric">
            {item.value === null || item.value === undefined || item.value === ""
              ? "—"
              : item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
