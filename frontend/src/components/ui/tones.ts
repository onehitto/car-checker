/** Dashboard-lamp tones, always shown with a text label. */
export type Tone = "ok" | "upcoming" | "soon" | "due" | "overdue" | "neutral";

const STATUS_TONES: Record<string, Tone> = {
  ok: "ok",
  valid: "ok",
  upcoming: "upcoming",
  due_soon: "soon",
  expiring_soon: "soon",
  due: "due",
  overdue: "overdue",
  expired: "overdue",
  unknown: "neutral",
  info: "neutral",
  low: "upcoming",
  medium: "soon",
  high: "due",
  critical: "overdue",
};

export function toneFor(status: string): Tone {
  return STATUS_TONES[status] ?? "neutral";
}
