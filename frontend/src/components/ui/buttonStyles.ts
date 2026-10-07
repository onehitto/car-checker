import { cn } from "@/lib/cn";

export type Variant = "primary" | "secondary" | "ghost" | "danger";
export type Size = "sm" | "md";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-ink text-white hover:bg-ink-soft",
  secondary: "border border-rule bg-sheet text-ink hover:border-steel",
  ghost: "text-ink hover:bg-paper",
  danger: "bg-overdue text-white hover:bg-[#9a1d14]",
};

const SIZES: Record<Size, string> = {
  sm: "h-8 gap-1.5 px-3 text-sm",
  md: "h-10 gap-2 px-4",
};

export function buttonClasses(variant: Variant = "primary", size: Size = "md"): string {
  return cn(
    "inline-flex shrink-0 items-center justify-center rounded-md font-medium whitespace-nowrap transition-colors",
    "disabled:cursor-not-allowed disabled:opacity-50",
    VARIANTS[variant],
    SIZES[size],
  );
}
