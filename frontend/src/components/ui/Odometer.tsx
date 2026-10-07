import { cn } from "@/lib/cn";

const DIGITS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"];

interface OdometerProps {
  /** Value to display (already converted to the display unit). */
  value: number;
  unit: string;
  /** Accessible text, e.g. "98,400 km". */
  label: string;
  size?: "sm" | "lg";
  minDigits?: number;
  className?: string;
}

/**
 * Mechanical odometer: one drum per digit, the last drum inverted like the tenths drum of a
 * real odometer. Drums roll to their new position when the value changes.
 */
export function Odometer({
  value,
  unit,
  label,
  size = "lg",
  minDigits = 6,
  className,
}: OdometerProps) {
  const digits = Math.max(0, Math.round(value)).toString().padStart(minDigits, "0").split("");
  const large = size === "lg";
  return (
    <div
      className={cn("inline-flex w-fit items-end gap-2", className)}
      role="img"
      aria-label={label}
      dir="ltr"
    >
      <div
        aria-hidden="true"
        className={cn(
          "flex gap-[3px] rounded-md bg-ink p-[3px] shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]",
          large ? "text-[44px] sm:text-[52px]" : "text-[17px]",
        )}
      >
        {digits.map((digit, index) => {
          const last = index === digits.length - 1;
          return (
            <span
              key={digits.length - index}
              className={cn(
                "relative block h-[1.15em] w-[0.72em] overflow-hidden rounded-[3px]",
                last ? "bg-overdue" : "bg-ink-soft",
              )}
            >
              <span
                className="absolute inset-x-0 top-0 flex flex-col font-display leading-[1.15em] font-semibold text-white numeric transition-transform duration-700 ease-[cubic-bezier(.2,.8,.2,1)]"
                style={{ transform: `translateY(-${Number(digit) * 1.15}em)` }}
              >
                {DIGITS.map((d) => (
                  <span key={d} className="block h-[1.15em] text-center">
                    {d}
                  </span>
                ))}
              </span>
              {/* drum curvature */}
              <span className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,rgba(0,0,0,0.35),transparent_30%,transparent_70%,rgba(0,0,0,0.35))]" />
            </span>
          );
        })}
      </div>
      <span
        aria-hidden="true"
        className={cn("font-display font-semibold opacity-60", large ? "pb-1 text-xl" : "text-sm")}
      >
        {unit}
      </span>
    </div>
  );
}
