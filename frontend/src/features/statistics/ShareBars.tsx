import { useFormat } from "@/lib/useFormat";

interface ShareItem {
  key: string;
  label: string;
  total: string;
  /** 0..1 */
  share: number;
  detail?: string;
}

/** Horizontal bars with the amount and the share of the total, largest first. */
export function ShareBars({ items, currency }: { items: ShareItem[]; currency: string }) {
  const format = useFormat();
  const sorted = [...items].sort((a, b) => Number(b.total) - Number(a.total));
  return (
    <ul className="flex flex-col gap-3">
      {sorted.map((item) => (
        <li key={item.key}>
          <div className="flex items-baseline justify-between gap-3">
            <span>
              {item.label}
              {item.detail && <span className="ms-2 text-sm text-steel">{item.detail}</span>}
            </span>
            <span className="numeric">
              <span className="font-medium">{format.money(item.total, currency)}</span>
              <span className="ms-2 inline-block w-12 text-end text-sm text-steel">
                {format.number(item.share * 100, 0)}%
              </span>
            </span>
          </div>
          <div className="mt-1 h-2 rounded-sm bg-paper" aria-hidden="true">
            <div
              className="h-2 rounded-sm bg-petrol"
              style={{ width: `${Math.max(1, Math.round(item.share * 100))}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
