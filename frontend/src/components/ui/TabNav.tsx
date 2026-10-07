import type { ReactNode } from "react";
import { NavLink } from "react-router";

import { cn } from "@/lib/cn";

export interface TabItem {
  to: string;
  label: ReactNode;
  end?: boolean;
}

interface TabNavProps {
  items: TabItem[];
  label: string;
  /** "secondary": smaller pills for the sections inside a tab. */
  variant?: "primary" | "secondary";
}

/** Route-based tabs: each tab is a URL, so it can be bookmarked and shared. */
export function TabNav({ items, label, variant = "primary" }: TabNavProps) {
  if (variant === "secondary") {
    return (
      <nav aria-label={label} className="-mx-1 overflow-x-auto">
        <ul className="flex min-w-max gap-1 px-1">
          {items.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "block rounded-full px-3 py-1 text-sm font-medium whitespace-nowrap transition-colors",
                    isActive ? "bg-ink text-white" : "text-steel hover:bg-sheet hover:text-ink",
                  )
                }
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    );
  }
  return (
    <nav aria-label={label} className="-mx-1 overflow-x-auto">
      <ul className="flex min-w-max gap-1 border-b border-rule px-1">
        {items.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "-mb-px block border-b-2 px-3 py-2.5 text-sm font-medium whitespace-nowrap transition-colors",
                  isActive
                    ? "border-petrol text-ink"
                    : "border-transparent text-steel hover:border-rule hover:text-ink",
                )
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
