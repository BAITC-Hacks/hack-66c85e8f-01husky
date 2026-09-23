import { format, parseISO } from "date-fns";
import { kk, ru } from "date-fns/locale";
import type { TaskStatus, Urgency } from "@/lib/api/types";

const DAY = 86_400_000;

/** 74.2 → "01:14", 3725 → "1:02:05" */
export function formatTimecode(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(r).padStart(2, "0");
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

/** 2710 → "45 мин" / "45 мин"; < 60 → "0:42" */
export function formatDuration(sec: number | null | undefined): string {
  if (!sec) return "—";
  if (sec < 60) return formatTimecode(sec);
  const m = Math.round(sec / 60);
  return m >= 60 ? `${Math.floor(m / 60)} ч ${m % 60} мин` : `${m} мин`;
}

export function formatDate(iso: string | null | undefined, locale: string, pattern = "d MMM yyyy"): string {
  if (!iso) return "—";
  return format(parseISO(iso), pattern, { locale: locale === "kk" ? kk : ru });
}

export function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export type DeadlineTone = "none" | "done" | "overdue" | "soon" | "ok";

/** Whole days from `today` to `deadline` (negative = overdue) and a tone for UI. */
export function deadlineInfo(
  deadline: string | null,
  status: TaskStatus,
  today: string = toISODate(new Date()),
): { days: number | null; tone: DeadlineTone } {
  if (!deadline) return { days: null, tone: "none" };
  const days = Math.round((parseISO(deadline).getTime() - parseISO(today).getTime()) / DAY);
  if (status === "done") return { days, tone: "done" };
  if (days < 0 || status === "overdue") return { days, tone: "overdue" };
  if (days <= 2) return { days, tone: "soon" };
  return { days, tone: "ok" };
}

/** "SPEAKER_03" → 3 (falls back to a stable hash for other labels) */
export function speakerIndex(label: string): number {
  const m = /(\d+)$/.exec(label);
  if (m) return Number(m[1]);
  let h = 0;
  for (const c of label) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return h;
}

export const SPEAKER_PALETTE_SIZE = 6;
export function speakerColor(label: string): string {
  return `var(--speaker-${speakerIndex(label) % SPEAKER_PALETTE_SIZE})`;
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join("");
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(0)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MB`;
  return `${(n / 1024 ** 3).toFixed(2)} GB`;
}

export const URGENCY_ORDER: Urgency[] = ["low", "normal", "high", "critical"];
export const TASK_STATUSES: TaskStatus[] = ["draft", "confirmed", "in_progress", "done", "overdue"];

/** Statuses a task may be moved to from the dashboard (spec §6). Includes `from` itself. */
export function allowedStatuses(from: TaskStatus): TaskStatus[] {
  if (from === "draft") return ["draft"];
  if (from === "overdue") return ["overdue", "in_progress", "done"];
  return ["confirmed", "in_progress", "done"];
}

export type DeadlineBucket = "overdue" | "today" | "tomorrow" | "week" | "later" | "none" | "done";
export const DEADLINE_BUCKETS: DeadlineBucket[] = [
  "overdue",
  "today",
  "tomorrow",
  "week",
  "later",
  "none",
  "done",
];

/** Groups a task for the agenda view: done last, overdue first, then by days left. */
export function deadlineBucket(
  deadline: string | null,
  status: TaskStatus,
  today: string = toISODate(new Date()),
): DeadlineBucket {
  if (status === "done") return "done";
  const { days, tone } = deadlineInfo(deadline, status, today);
  if (tone === "overdue") return "overdue";
  if (days === null) return "none";
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  return days <= 7 ? "week" : "later";
}

/** Confidence under this is flagged for the secretary (spec §12: "LLM выдумывает"). */
export const LOW_CONFIDENCE = 0.7;
