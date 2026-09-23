/**
 * In-memory mock database, persisted to localStorage so the demo survives
 * reloads. Open any page with `?reset-mocks` to start over.
 */
import type {
  Direction,
  Meeting,
  MeetingDetail,
  Notification,
  Participant,
  Segment,
  SpeakerMapping,
  Task,
  User,
} from "@/lib/api/types";
import {
  buildSegments,
  buildTasks,
  MODEL_INFO,
  seedDirections,
  seedMeetingParticipants,
  seedMeetings,
  seedNotifications,
  seedParticipants,
  seedSegments,
  seedSpeakerMaps,
  seedTasks,
  seedUsers,
  TEMPLATE_SUMMARY,
} from "./seed";

const KEY = "kenes-mock-db-v4";

/* Stored rows. Handlers derive the rest (counts, names, titles) the way the backend does. */
export type UserRow = Omit<User, "participant_id"> & { password: string };
export type MeetingRow = Omit<Meeting, "tasks_count" | "participants_count"> &
  Pick<MeetingDetail, "summary" | "language_stats" | "model_info">;
export type TaskRow = Omit<Task, "direction_name" | "meeting_title" | "meeting_date">;
export type NotificationRow = Notification & { user_id: number };

export interface DB {
  users: UserRow[];
  sessionUserId: number | null;
  participants: Participant[];
  directions: Direction[];
  meetings: MeetingRow[];
  meetingParticipants: Record<number, number[]>;
  speakerMaps: Record<number, SpeakerMapping[]>;
  segments: Record<number, Segment[]>;
  tasks: TaskRow[];
  notifications: NotificationRow[];
  /** meeting id → processing start (ms) */
  processing: Record<number, number>;
  seq: number;
}

function fresh(): DB {
  return {
    users: structuredClone(seedUsers),
    sessionUserId: null,
    participants: structuredClone(seedParticipants),
    directions: structuredClone(seedDirections),
    meetings: seedMeetings(),
    meetingParticipants: structuredClone(seedMeetingParticipants),
    speakerMaps: structuredClone(seedSpeakerMaps),
    segments: seedSegments(),
    tasks: seedTasks(),
    notifications: seedNotifications(),
    processing: { 102: Date.now() },
    seq: 200,
  };
}

function load(): DB {
  if (typeof window === "undefined") return fresh();
  try {
    if (new URLSearchParams(window.location.search).has("reset-mocks")) {
      localStorage.removeItem(KEY);
    }
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw) as DB;
  } catch {
    /* storage unavailable */
  }
  return fresh();
}

export const db: DB = load();

export function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(db));
  } catch {
    /* ignore */
  }
}

export const nextId = () => ++db.seq;
export const now = () => new Date().toISOString();

/* ---------- simulated pipeline ---------- */

export const STAGES = ["stt", "diarize", "voiceprint", "extract", "summary"] as const;
const TOTAL_MS = 20_000;
const UPLOAD_MS = 1_500;

export function tickProcessing() {
  let changed = false;
  for (const [idStr, started] of Object.entries(db.processing)) {
    const id = Number(idStr);
    const m = db.meetings.find((x) => x.id === id);
    if (!m) {
      delete db.processing[id];
      continue;
    }
    const elapsed = Date.now() - started;
    if (elapsed < 0) {
      m.status = "processing";
      m.progress_stage = "bot_joining";
      m.progress_pct = 0;
    } else if (elapsed < UPLOAD_MS) {
      m.status = "uploaded";
      m.progress_stage = "queued";
      m.progress_pct = 0;
    } else if (elapsed < TOTAL_MS) {
      const pct = (elapsed - UPLOAD_MS) / (TOTAL_MS - UPLOAD_MS);
      m.status = "processing";
      m.progress_pct = Math.round(pct * 1000) / 10;
      m.progress_stage = STAGES[Math.min(STAGES.length - 1, Math.floor(pct * STAGES.length))];
    } else {
      finalize(m);
      delete db.processing[id];
    }
    changed = true;
  }
  if (changed) save();
}

function finalize(m: MeetingRow) {
  const pids = db.meetingParticipants[m.id] ?? [];
  const pick = (i: number) => pids[i] ?? null;
  m.status = "draft";
  m.progress_stage = "done";
  m.progress_pct = 100;
  m.duration_sec = m.duration_sec ?? 184;
  m.summary = TEMPLATE_SUMMARY;
  m.language_stats = { ru: 0.57, kk: 0.21, mixed: 0.22 };
  m.model_info = MODEL_INFO;
  db.segments[m.id] = buildSegments();
  db.speakerMaps[m.id] = [
    { speaker: "SPEAKER_00", participant_id: pick(0), source: pick(0) ? "voiceprint" : "none", confidence: pick(0) ? 0.9 : 0 },
    { speaker: "SPEAKER_01", participant_id: pick(1), source: pick(1) ? "llm" : "none", confidence: pick(1) ? 0.72 : 0 },
    { speaker: "SPEAKER_02", participant_id: null, source: "none", confidence: 0 },
    { speaker: "SPEAKER_03", participant_id: pick(3), source: pick(3) ? "voiceprint" : "none", confidence: pick(3) ? 0.81 : 0 },
  ];
  db.tasks = db.tasks.filter((t) => t.meeting_id !== m.id);
  const base = nextId();
  db.seq += 10;
  db.tasks.push(...buildTasks(m.id, m.meeting_date, base, () => null));
  notify({
    kind: "protocol_ready",
    meeting_id: m.id,
    task_id: null,
    title: "Черновик протокола готов",
    body: `${m.title} — проверьте спикеров и поручения`,
  });
}

export function startProcessing(m: MeetingRow) {
  db.processing[m.id] = Date.now();
  m.status = "uploaded";
  m.progress_stage = null;
  m.progress_pct = 0;
  m.error = null;
}

export function notify(n: Pick<Notification, "kind" | "meeting_id" | "task_id" | "title" | "body">) {
  db.notifications.unshift({
    ...n,
    id: nextId(),
    user_id: db.sessionUserId ?? 1,
    read_at: null,
    created_at: now(),
  });
}

/* ---------- derived task state ---------- */

const today = () => new Date().toISOString().slice(0, 10);

export function refreshOverdue() {
  const t0 = today();
  for (const t of db.tasks) {
    if (t.deadline && t.deadline < t0 && (t.status === "confirmed" || t.status === "in_progress")) {
      t.status = "overdue";
    }
  }
}

export function isDueSoon(t: TaskRow) {
  if (!t.deadline || !(t.status === "confirmed" || t.status === "in_progress")) return false;
  const diff = new Date(t.deadline).getTime() - new Date(today()).getTime();
  return diff >= 0 && diff <= 86_400_000;
}
