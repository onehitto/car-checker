import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface PanelProps {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}

/** White sheet on the paper background, separated by a hairline rule. */
export function Panel({ title, actions, children, className, bodyClassName }: PanelProps) {
  return (
    <section className={cn("rounded-panel border border-rule bg-sheet", className)}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-rule px-4 py-3">
          {title && <h2 className="text-lg leading-tight">{title}</h2>}
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={cn("p-4", bodyClassName)}>{children}</div>
    </section>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-3xl leading-tight sm:text-4xl">{title}</h1>
        {description && <p className="mt-1 max-w-prose text-steel">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
