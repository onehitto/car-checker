/** Monthly totals from the API only list months with expenses: add the empty months between. */
export function fillMonths(months: { month: string; total: string }[]): {
  month: string;
  total: number;
}[] {
  if (months.length === 0) return [];
  const totals = new Map(months.map((item) => [item.month, Number(item.total)]));
  const sorted = [...totals.keys()].sort();
  const [firstYear = 0, firstMonth = 1] = sorted[0]!.split("-").map(Number);
  const last = sorted[sorted.length - 1]!;
  const result: { month: string; total: number }[] = [];
  for (let year = firstYear, month = firstMonth; ; month++) {
    if (month > 12) {
      month = 1;
      year++;
    }
    const key = `${year}-${String(month).padStart(2, "0")}`;
    result.push({ month: key, total: totals.get(key) ?? 0 });
    if (key >= last) break;
  }
  return result;
}
