/**
 * API types, hand-written from the spec (§5–§7) until the backend exposes
 * /openapi.json. Then run `pnpm gen:api` and switch imports to the generated file.
 */

export type Locale = "ru" | "kk";
export type Role = "user" | "admin";
export type Urgency = "low" | "normal" | "high" | "critical";
export type SpeakerSource = "voiceprint" | "llm" | "manual" | "none";
export type SegmentLang = "ru" | "kk" | "mixed" | "other";
export type MeetingSource = "upload" | "live" | "bot";
export type Platform = "meet" | "zoom" | "teams";
export type MeetingStatus = "uploaded" | "processing" | "draft" | "confirmed" | "failed";
export type TaskStatus = "draft" | "confirmed" | "in_progress" | "done" | "overdue";
export type NotificationKind = "assigned" | "due_soon" | "overdue" | "protocol_ready";
export type ExportFormat = "docx" | "pdf";

/** ISO date "2026-09-23" */
export type ISODate = string;
/** ISO datetime */
export type ISODateTime = string;

export interface User {
  id: number;
  email: string;
  name: string;
  role: Role;
  locale: Locale;
  created_at: ISODateTime;
}

export interface Participant {
  id: number;
  name: string;
  email: string | null;
  position: string | null;
  user_id: number | null;
  has_voiceprint: boolean;
  created_at: ISODateTime;
}

export interface Direction {
  id: number;
  name: string;
  is_active: boolean;
}

export interface Meeting {
  id: number;
  title: string;
  meeting_date: ISODate;
  source: MeetingSource;
  platform: Platform | null;
  has_audio: boolean;
  duration_sec: number | null;
  output_language: Locale;
  status: MeetingStatus;
  progress_stage: string | null;
  progress_pct: number | null;
  summary: string | null;
  language_stats: Record<string, number> | null;
  model_info: Record<string, string> | null;
  error: string | null;
  sed_ref: string | null;
  created_by: number;
  created_at: ISODateTime;
  confirmed_at: ISODateTime | null;
}

export interface MeetingListItem
  extends Pick<
    Meeting,
    | "id"
    | "title"
    | "meeting_date"
    | "source"
    | "platform"
    | "status"
    | "progress_pct"
    | "duration_sec"
    | "output_language"
    | "created_at"
  > {
  tasks_count: number;
  participants: Pick<Participant, "id" | "name">[];
}

export interface Segment {
  id: number;
  idx: number;
  start: number;
  end: number;
  speaker: string;
  text: string;
  lang: SegmentLang;
}

export interface SpeakerMapping {
  speaker: string;
  participant_id: number | null;
  source: SpeakerSource;
  confidence: number;
}

export interface Task {
  id: number;
  meeting_id: number;
  meeting_title?: string;
  assignee_participant_id: number | null;
  assignee_name: string;
  text: string;
  deadline: ISODate | null;
  deadline_raw: string | null;
  urgency: Urgency;
  direction_id: number;
  quote: string;
  segment_idx: number;
  confidence: number;
  status: TaskStatus;
  sed_ref: string | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  done_at: ISODateTime | null;
}

export interface MeetingDetail {
  meeting: Meeting;
  participants: Participant[];
  segments: Segment[];
  speaker_map: SpeakerMapping[];
  tasks: Task[];
  summary: string | null;
}

export interface TaskStats {
  draft: number;
  confirmed: number;
  in_progress: number;
  done: number;
  overdue: number;
  due_soon: number;
}

export interface Notification {
  id: number;
  user_id: number;
  task_id: number | null;
  meeting_id: number | null;
  kind: NotificationKind;
  title: string;
  body: string;
  read_at: ISODateTime | null;
  created_at: ISODateTime;
}

/* ---- request bodies ---- */

export interface RegisterBody {
  email: string;
  password: string;
  name: string;
  locale: Locale;
}
export interface LoginBody {
  email: string;
  password: string;
}
export interface ParticipantCreate {
  name: string;
  email?: string | null;
  position?: string | null;
}
export interface MeetingCommon {
  title: string;
  meeting_date: ISODate;
  participant_ids: number[];
}
export interface MeetingLiveCreate extends MeetingCommon {
  output_language: Locale;
}
export interface MeetingBotCreate extends MeetingCommon {
  platform: Platform;
  url: string;
}
export interface MeetingPatch {
  title?: string;
  meeting_date?: ISODate;
  summary?: string;
}
export interface SpeakerAssign {
  speaker: string;
  participant_id: number | null;
}
export interface TaskCreate {
  meeting_id: number;
  text: string;
  assignee_participant_id?: number | null;
  assignee_name?: string;
  deadline?: ISODate | null;
  urgency?: Urgency;
  direction_id?: number;
}
export interface TaskPatch {
  text?: string;
  assignee_participant_id?: number | null;
  deadline?: ISODate | null;
  urgency?: Urgency;
  direction_id?: number;
  status?: TaskStatus;
}
export interface TaskFilters {
  status?: TaskStatus;
  assignee_id?: number;
  direction_id?: number;
  urgency?: Urgency;
  meeting_id?: number;
  mine?: boolean;
}
export interface MeetingFilters {
  status?: MeetingStatus;
  from?: ISODate;
  to?: ISODate;
}
