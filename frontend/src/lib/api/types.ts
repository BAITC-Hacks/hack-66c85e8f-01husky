/**
 * API types. Aliases over `schema.gen.ts`, which `pnpm gen:api` generates from the
 * backend's /openapi.json. Don't hand-write response shapes here: regenerate instead.
 * Only narrowing the schema can't express (plain `string` fields with a known set of values) lives here.
 */

import type { components } from "./schema.gen";

type S = components["schemas"];
/**
 * Generated with `--default-non-nullable false`, so fields with a default are optional.
 * That's right for request bodies, but the backend always serializes every field in a
 * response, so response types go through `Out<>`.
 */
type Out<K extends keyof S> = Required<S[K]>;

export type Locale = S["Locale"];
export type Role = S["UserRole"];
export type Urgency = S["Urgency"];
export type SpeakerSource = S["SpeakerSource"];
export type MeetingSource = S["MeetingSource"];
export type MeetingStatus = S["MeetingStatus"];
export type TaskStatus = S["TaskStatus"];
export type NotificationKind = S["NotificationKind"];
export type SegmentLang = "ru" | "kk" | "mixed" | "other";
export type Platform = "meet" | "zoom" | "teams";
export type ExportFormat = "docx" | "pdf";

/** ISO date "2026-09-23" */
export type ISODate = string;
/** ISO datetime */
export type ISODateTime = string;

export type User = Out<"UserOut">;
export type Participant = Out<"ParticipantOut">;
export type Direction = Out<"DirectionOut">;
export type Task = Out<"TaskOut">;
export type TaskStats = Out<"TaskStats">;
export type Notification = Out<"NotificationOut">;
export type UnreadCount = Out<"UnreadCount">;
export type SpeakerMapping = Out<"SpeakerMapOut">;

export type Segment = Omit<Out<"SegmentOut">, "lang"> & { lang: SegmentLang };

/** Meeting as returned by list/create/reprocess. `progress_pct` is 0–100. */
export type Meeting = Omit<Out<"MeetingOut">, "platform"> & { platform: Platform | null };
export type MeetingListItem = Meeting;

/** GET /meetings/{id}: the meeting fields plus its content, flat. */
export type MeetingDetail = Omit<
  Out<"MeetingDetail">,
  "platform" | "participants" | "segments" | "speaker_map" | "tasks" | "language_stats" | "model_info"
> & {
  platform: Platform | null;
  participants: Participant[];
  segments: Segment[];
  speaker_map: SpeakerMapping[];
  tasks: Task[];
  language_stats: Record<string, number> | null;
  model_info: Record<string, string> | null;
};

export const hasAudio = (m: Pick<Meeting, "audio_path">) => m.audio_path != null;

/* ---- request bodies ---- */

export type RegisterBody = S["RegisterIn"];
export type LoginBody = S["LoginIn"];
export type ParticipantCreate = S["ParticipantIn"];
export type ParticipantPatch = S["ParticipantPatch"];
export type MeetingLiveCreate = S["LiveMeetingIn"];
export type MeetingBotCreate = Omit<S["BotMeetingIn"], "platform"> & { platform: Platform };
export type MeetingPatch = S["MeetingPatch"];
export type SpeakerAssign = S["SpeakerMapIn"];
export type TaskCreate = S["TaskCreate"];
export type TaskPatch = S["TaskPatch"];
export type DirectionCreate = S["DirectionIn"];
export type DirectionPatch = S["DirectionPatch"];

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
  date_from?: ISODate;
  date_to?: ISODate;
}
