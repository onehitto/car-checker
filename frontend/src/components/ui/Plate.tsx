import { cn } from "@/lib/cn";

/** License plate as printed on the car (always left-to-right, even in Arabic). */
export function Plate({ value, className }: { value: string; className?: string }) {
  return (
    <span
      dir="ltr"
      className={cn(
        "inline-flex items-center rounded-[4px] border-2 border-ink bg-white px-2 py-px font-display text-sm font-bold tracking-wider text-ink",
        className,
      )}
    >
      {value}
    </span>
  );
}
