import * as Menu from "@radix-ui/react-dropdown-menu";
import { Ellipsis } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export interface RowAction {
  label: ReactNode;
  onSelect: () => void;
  icon?: ReactNode;
  danger?: boolean;
}

/** "More" menu at the end of a row. Falsy entries are skipped (actions the role does not allow). */
export function RowMenu({
  label,
  actions,
}: {
  label: string;
  actions: (RowAction | false | null | undefined)[];
}) {
  const items = actions.filter(Boolean) as RowAction[];
  if (items.length === 0) return null;
  return (
    <Menu.Root modal={false}>
      <Menu.Trigger
        aria-label={label}
        className="rounded-md p-1.5 text-steel hover:bg-paper hover:text-ink data-[state=open]:bg-paper"
      >
        <Ellipsis className="size-5" aria-hidden="true" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Content
          align="end"
          sideOffset={4}
          className="z-50 min-w-44 rounded-md border border-rule bg-sheet p-1 shadow-lg"
        >
          {items.map((item, index) => (
            <Menu.Item
              key={index}
              onSelect={item.onSelect}
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded px-2.5 py-1.5 text-sm outline-none select-none",
                "data-[highlighted]:bg-paper [&>svg]:size-4",
                item.danger ? "text-overdue" : "text-ink",
              )}
            >
              {item.icon}
              {item.label}
            </Menu.Item>
          ))}
        </Menu.Content>
      </Menu.Portal>
    </Menu.Root>
  );
}
