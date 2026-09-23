/**
 * MSW handlers for every backend endpoint (spec §7, shapes from /openapi.json). Stateful: confirm,
 * speakers, task edits etc. mutate the mock db the way the backend does.
 */
import { delay, http, HttpResponse, type PathParams } from "msw";
import type {
  Locale,
  Meeting,
  MeetingBotCreate,
  MeetingDetail,
  MeetingLiveCreate,
  MeetingPatch,
  Notification,
  Participant,
  SpeakerAssign,
  Task,
  TaskCreate,
  TaskPatch,
  TaskStats,
  TaskStatus,
  User,
} from "@/lib/api/types";
import {
  db,
  isDueSoon,
  type MeetingRow,
  nextId,
  notify,
  type NotificationRow,
  now,
  refreshOverdue,
  save,
  startProcessing,
  type TaskRow,
  tickProcessing,
  type UserRow,
} from "./db";
import { MINIMAL_PDF } from "./pdf";

const A = (p: string) => `*/api/v1${p}`;
const detail = (status: number, msg: string) => HttpResponse.json({ detail: msg }, { status });
const lag = () => delay(120 + Math.random() * 180);

function me() {
  return db.users.find((u) => u.id === db.sessionUserId) ?? null;
}
function publicUser(u: UserRow): User {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { password, ...rest } = u;
  return { ...rest, participant_id: db.participants.find((p) => p.user_id === u.id)?.id ?? null };
}
function authed(fn: (args: { request: Request; params: PathParams }) => Promise<Response> | Response) {
  return async ({ request, params }: { request: Request; params: PathParams }) => {
    await lag();
    if (!me()) return detail(401, "Not authenticated");
    const res = await fn({ request, params });
    save();
    return res;
  };
}
const num = (v: unknown) => Number(v);
const meetingById = (id: number) => db.meetings.find((m) => m.id === id);

/** Like the backend's task_out(): adds direction and meeting names. */
function withTitle(t: TaskRow): Task {
  const m = meetingById(t.meeting_id);
  return {
    ...t,
    direction_name: db.directions.find((d) => d.id === t.direction_id)?.name ?? null,
    meeting_title: m?.title ?? null,
    meeting_date: m?.meeting_date ?? null,
  };
}

/** Like the backend's meeting_out(): MeetingOut without the heavy content. */
function meetingOut(m: MeetingRow): Meeting {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { summary, language_stats, model_info, ...rest } = m;
  return {
    ...rest,
    tasks_count: db.tasks.filter((t) => t.meeting_id === m.id).length,
    participants_count: (db.meetingParticipants[m.id] ?? []).length,
  };
}

function detailOf(m: MeetingRow): MeetingDetail {
  const pids = db.meetingParticipants[m.id] ?? [];
  return {
    ...meetingOut(m),
    summary: m.summary,
    language_stats: m.language_stats,
    model_info: m.model_info,
    participants: db.participants.filter((p) => pids.includes(p.id)),
    segments: db.segments[m.id] ?? [],
    speaker_map: db.speakerMaps[m.id] ?? [],
    tasks: db.tasks.filter((t) => t.meeting_id === m.id).map(withTitle),
  };
}

function newMeeting(fields: Partial<MeetingRow> & Pick<MeetingRow, "title" | "meeting_date" | "source">): MeetingRow {
  const m: MeetingRow = {
    id: nextId(),
    platform: null,
    audio_path: null,
    duration_sec: null,
    output_language: "ru",
    status: "uploaded",
    progress_stage: null,
    progress_pct: 0,
    summary: null,
    language_stats: null,
    model_info: null,
    error: null,
    sed_ref: null,
    created_by: db.sessionUserId ?? 1,
    created_at: now(),
    confirmed_at: null,
    ...fields,
  };
  db.meetings.unshift(m);
  return m;
}

function notificationOut(n: NotificationRow): Notification {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user_id, ...rest } = n;
  return rest;
}

/** Recalculate assignees after a manual speaker fix (spec §5.2). */
function reassign(meetingId: number, speaker: string, oldPid: number | null, newPid: number | null) {
  const newP = db.participants.find((p) => p.id === newPid);
  const first = newP?.name.split(" ")[0]?.toLowerCase();
  for (const t of db.tasks) {
    if (t.meeting_id !== meetingId) continue;
    if (oldPid && t.assignee_participant_id === oldPid && newPid) t.assignee_participant_id = newPid;
    else if (!t.assignee_participant_id && first && t.assignee_name.toLowerCase().startsWith(first.slice(0, 4))) {
      t.assignee_participant_id = newPid;
      t.confidence = Math.max(t.confidence, 0.9);
    }
    t.updated_at = now();
  }
  void speaker;
}

export const handlers = [
  /* ---------------- auth ---------------- */
  http.post(A("/auth/login"), async ({ request }) => {
    await lag();
    const { email } = (await request.json()) as { email: string; password: string };
    // Mock mode: any password works; unknown emails log in as the demo admin.
    const u = db.users.find((x) => x.email === email) ?? db.users[0];
    db.sessionUserId = u.id;
    save();
    return HttpResponse.json(publicUser(u));
  }),
  http.post(A("/auth/register"), async ({ request }) => {
    await lag();
    const body = (await request.json()) as { email: string; password: string; name: string; locale: Locale };
    if (db.users.some((u) => u.email === body.email)) return detail(409, "Email already registered");
    const u = { id: nextId(), role: "user" as const, created_at: now(), ...body };
    db.users.push(u);
    const p = db.participants.find((x) => x.email === body.email);
    if (p) p.user_id = u.id;
    db.sessionUserId = u.id;
    save();
    return HttpResponse.json(publicUser(u), { status: 201 });
  }),
  http.post(A("/auth/logout"), async () => {
    db.sessionUserId = null;
    save();
    return new HttpResponse(null, { status: 204 });
  }),
  http.get(A("/auth/me"), async () => {
    await lag();
    const u = me();
    return u ? HttpResponse.json(publicUser(u)) : detail(401, "Not authenticated");
  }),

  /* ---------------- participants ---------------- */
  http.get(A("/participants"), authed(() => HttpResponse.json(db.participants))),
  http.post(A("/participants"), authed(async ({ request }) => {
    const body = (await request.json()) as Partial<Participant>;
    const p: Participant = {
      id: nextId(),
      name: body.name ?? "Гость",
      email: body.email || null,
      position: body.position || null,
      user_id: null,
      has_voiceprint: false,
      created_at: now(),
    };
    db.participants.push(p);
    return HttpResponse.json(p, { status: 201 });
  })),
  http.patch(A("/participants/:id"), authed(async ({ request, params }) => {
    const p = db.participants.find((x) => x.id === num(params.id));
    if (!p) return detail(404, "Participant not found");
    Object.assign(p, await request.json());
    return HttpResponse.json(p);
  })),
  http.post(A("/participants/:id/voiceprint"), authed(async ({ params }) => {
    const p = db.participants.find((x) => x.id === num(params.id));
    if (!p) return detail(404, "Participant not found");
    await delay(900);
    p.has_voiceprint = true;
    return HttpResponse.json({ ok: true, embedding_dim: 192 });
  })),
  http.delete(A("/participants/:id/voiceprint"), authed(({ params }) => {
    const p = db.participants.find((x) => x.id === num(params.id));
    if (!p) return detail(404, "Participant not found");
    p.has_voiceprint = false;
    return new HttpResponse(null, { status: 204 });
  })),

  /* ---------------- directions ---------------- */
  http.get(A("/directions"), authed(() => HttpResponse.json(db.directions))),
  http.post(A("/directions"), authed(async ({ request }) => {
    if (me()!.role !== "admin") return detail(403, "Admin only");
    const { name } = (await request.json()) as { name: string };
    if (db.directions.some((d) => d.name.toLowerCase() === name.toLowerCase())) return detail(409, "Direction exists");
    const d = { id: nextId(), name, is_active: true };
    db.directions.push(d);
    return HttpResponse.json(d, { status: 201 });
  })),
  http.patch(A("/directions/:id"), authed(async ({ request, params }) => {
    if (me()!.role !== "admin") return detail(403, "Admin only");
    const d = db.directions.find((x) => x.id === num(params.id));
    if (!d) return detail(404, "Direction not found");
    Object.assign(d, await request.json());
    return HttpResponse.json(d);
  })),

  /* ---------------- meetings ---------------- */
  http.get(A("/meetings"), authed(({ request }) => {
    tickProcessing();
    const q = new URL(request.url).searchParams;
    const status = q.get("status");
    const from = q.get("date_from");
    const to = q.get("date_to");
    const list: Meeting[] = db.meetings
      .filter((m) => (!status || m.status === status) && (!from || m.meeting_date >= from) && (!to || m.meeting_date <= to))
      .map(meetingOut);
    return HttpResponse.json(list);
  })),

  http.post(A("/meetings"), authed(async ({ request }) => {
    const form = await request.formData();
    const file = form.get("file") as File | null;
    if (!file) return detail(422, "file is required");
    const m = newMeeting({
      title: String(form.get("title") ?? "Без названия"),
      meeting_date: String(form.get("meeting_date")),
      output_language: (form.get("output_language") as Locale) ?? "ru",
      source: "upload",
    });
    m.audio_path = `data/audio/${m.id}/audio.wav`;
    db.meetingParticipants[m.id] = form.getAll("participant_ids").map(Number);
    startProcessing(m);
    return HttpResponse.json(meetingOut(m), { status: 201 });
  })),

  http.post(A("/meetings/live"), authed(async ({ request }) => {
    const body = (await request.json()) as MeetingLiveCreate;
    const { participant_ids = [], ...fields } = body;
    const m = newMeeting({ ...fields, source: "live" });
    db.meetingParticipants[m.id] = participant_ids;
    return HttpResponse.json(meetingOut(m), { status: 201 });
  })),

  http.post(A("/meetings/bot"), authed(async ({ request }) => {
    const body = (await request.json()) as MeetingBotCreate;
    const m = newMeeting({
      title: body.title,
      meeting_date: body.meeting_date,
      source: "bot",
      platform: body.platform,
      output_language: body.output_language,
      status: "processing",
      progress_stage: "bot_joining",
    });
    db.meetingParticipants[m.id] = body.participant_ids ?? [];
    // pretend the bot records for a bit, then uploads
    db.processing[m.id] = Date.now() + 4_000;
    m.audio_path = `data/audio/${m.id}/audio.wav`;
    return HttpResponse.json(meetingOut(m), { status: 201 });
  })),

  http.post(A("/meetings/:id/audio"), authed(({ params }) => {
    const m = meetingById(num(params.id));
    if (!m) return detail(404, "Meeting not found");
    if (m.status === "confirmed") return detail(409, "Confirmed protocol cannot be replaced");
    m.audio_path = `data/audio/${m.id}/audio.wav`;
    startProcessing(m);
    return HttpResponse.json(meetingOut(m));
  })),

  http.get(A("/meetings/:id"), authed(({ params }) => {
    tickProcessing();
    refreshOverdue();
    const m = meetingById(num(params.id));
    return m ? HttpResponse.json(detailOf(m)) : detail(404, "Meeting not found");
  })),

  http.patch(A("/meetings/:id"), authed(async ({ request, params }) => {
    const m = meetingById(num(params.id));
    if (!m) return detail(404, "Meeting not found");
    const { participant_ids, ...fields } = (await request.json()) as MeetingPatch;
    Object.assign(m, fields);
    if (participant_ids) db.meetingParticipants[m.id] = participant_ids;
    return HttpResponse.json(detailOf(m));
  })),

  http.put(A("/meetings/:id/speakers"), authed(async ({ request, params }) => {
    const id = num(params.id);
    const m = meetingById(id);
    if (!m) return detail(404, "Meeting not found");
    const body = (await request.json()) as SpeakerAssign[];
    const map = db.speakerMaps[id] ?? [];
    for (const a of body) {
      const row = map.find((r) => r.speaker === a.speaker);
      const old = row?.participant_id ?? null;
      if (row) Object.assign(row, { participant_id: a.participant_id, source: "manual", confidence: 1 });
      else map.push({ speaker: a.speaker, participant_id: a.participant_id, source: "manual", confidence: 1 });
      reassign(id, a.speaker, old, a.participant_id);
    }
    db.speakerMaps[id] = map;
    return HttpResponse.json(detailOf(m));
  })),

  http.post(A("/meetings/:id/reprocess"), authed(({ params }) => {
    const m = meetingById(num(params.id));
    if (!m) return detail(404, "Meeting not found");
    if (!m.audio_path) return detail(409, "Audio was deleted, cannot reprocess");
    if (m.status === "confirmed") return detail(409, "Confirmed protocol cannot be reprocessed");
    if (m.status === "processing") return detail(409, "Meeting is already being processed");
    startProcessing(m);
    return HttpResponse.json(meetingOut(m));
  })),

  http.post(A("/meetings/:id/confirm"), authed(({ params }) => {
    const m = meetingById(num(params.id));
    if (!m) return detail(404, "Meeting not found");
    if (m.status !== "draft") return detail(409, `Cannot confirm meeting in status ${m.status}`);
    m.status = "confirmed";
    m.confirmed_at = now();
    const tasks = db.tasks.filter((t) => t.meeting_id === m.id && t.status === "draft");
    for (const t of tasks) {
      t.status = "confirmed";
      t.updated_at = now();
      const p = db.participants.find((x) => x.id === t.assignee_participant_id);
      notify({
        kind: "assigned",
        task_id: t.id,
        meeting_id: m.id,
        title: p ? `Поручение: ${p.name}` : "Новое поручение",
        body: t.text,
      });
    }
    refreshOverdue();
    notify({
      kind: "protocol_ready",
      task_id: null,
      meeting_id: m.id,
      title: "Протокол утверждён",
      body: `${m.title} · ${tasks.length} поручений разосланы`,
    });
    return HttpResponse.json(detailOf(m));
  })),

  http.get(A("/meetings/:id/export"), authed(async ({ request, params }) => {
    const m = meetingById(num(params.id));
    if (!m) return detail(404, "Meeting not found");
    const format = new URL(request.url).searchParams.get("format") ?? "pdf";
    await delay(600);
    const name = `protocol-${m.id}.${format}`;
    if (format === "pdf") {
      return new HttpResponse(MINIMAL_PDF(m.title), {
        headers: { "Content-Type": "application/pdf", "Content-Disposition": `attachment; filename="${name}"` },
      });
    }
    return new HttpResponse(`Mock DOCX export for meeting #${m.id}: ${m.title}`, {
      headers: {
        "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "Content-Disposition": `attachment; filename="${name}"`,
      },
    });
  })),

  http.post(A("/meetings/:id/sed"), authed(async ({ params }) => {
    const m = meetingById(num(params.id));
    if (!m) return detail(404, "Meeting not found");
    if (m.status !== "confirmed") return detail(409, "Confirm the protocol before sending to SED");
    await delay(700);
    m.sed_ref = m.sed_ref ?? `SED-2026-${String(120 + (m.id % 1000)).padStart(6, "0")}`;
    for (const t of db.tasks) if (t.meeting_id === m.id) t.sed_ref = m.sed_ref;
    return HttpResponse.json({ sed_ref: m.sed_ref, outbox_path: `outbox/${m.id}/protocol.pdf` });
  })),

  http.delete(A("/meetings/:id/audio"), authed(({ params }) => {
    const m = meetingById(num(params.id));
    if (!m) return detail(404, "Meeting not found");
    if (m.status === "processing") return detail(409, "Meeting is being processed");
    m.audio_path = null;
    return new HttpResponse(null, { status: 204 });
  })),

  http.delete(A("/meetings/:id"), authed(({ params }) => {
    const id = num(params.id);
    db.meetings = db.meetings.filter((m) => m.id !== id);
    db.tasks = db.tasks.filter((t) => t.meeting_id !== id);
    delete db.processing[id];
    return new HttpResponse(null, { status: 204 });
  })),

  /* ---------------- tasks ---------------- */
  http.get(A("/tasks/stats"), authed(() => {
    refreshOverdue();
    const c = (s: TaskStatus) => db.tasks.filter((t) => t.status === s).length;
    return HttpResponse.json<TaskStats>({
      draft: c("draft"),
      confirmed: c("confirmed"),
      in_progress: c("in_progress"),
      done: c("done"),
      overdue: c("overdue"),
      due_soon: db.tasks.filter(isDueSoon).length,
      total: db.tasks.length,
    });
  })),

  http.get(A("/tasks"), authed(({ request }) => {
    refreshOverdue();
    const q = new URL(request.url).searchParams;
    const mine = q.get("mine") === "1";
    const myPids = db.participants.filter((p) => p.user_id === db.sessionUserId).map((p) => p.id);
    const eq = (k: string, v: unknown) => !q.get(k) || String(v) === q.get(k);
    const list = db.tasks
      .filter(
        (t) =>
          eq("status", t.status) &&
          eq("assignee_id", t.assignee_participant_id) &&
          eq("direction_id", t.direction_id) &&
          eq("urgency", t.urgency) &&
          eq("meeting_id", t.meeting_id) &&
          (!mine || (t.assignee_participant_id !== null && myPids.includes(t.assignee_participant_id))),
      )
      .map(withTitle);
    return HttpResponse.json(list);
  })),

  http.post(A("/tasks"), authed(async ({ request }) => {
    const body = (await request.json()) as TaskCreate;
    const p = db.participants.find((x) => x.id === body.assignee_participant_id);
    const t: TaskRow = {
      id: nextId(),
      meeting_id: body.meeting_id,
      assignee_participant_id: body.assignee_participant_id ?? null,
      assignee_name: body.assignee_name || p?.name || "",
      text: body.text,
      deadline: body.deadline ?? null,
      deadline_raw: body.deadline_raw ?? null,
      urgency: body.urgency ?? "normal",
      direction_id: body.direction_id ?? null,
      quote: body.quote ?? null,
      segment_idx: body.segment_idx ?? null,
      confidence: 1,
      status: meetingById(body.meeting_id)?.status === "confirmed" ? "confirmed" : "draft",
      sed_ref: null,
      created_at: now(),
      updated_at: now(),
      done_at: null,
    };
    db.tasks.push(t);
    return HttpResponse.json(withTitle(t), { status: 201 });
  })),

  http.patch(A("/tasks/:id"), authed(async ({ request, params }) => {
    const t = db.tasks.find((x) => x.id === num(params.id));
    if (!t) return detail(404, "Task not found");
    const body = (await request.json()) as TaskPatch;
    if ("assignee_participant_id" in body) {
      const p = db.participants.find((x) => x.id === body.assignee_participant_id);
      if (p) t.assignee_name = p.name;
    }
    Object.assign(t, body, { updated_at: now() });
    if (body.status === "done") t.done_at = now();
    if (body.status && body.status !== "done") t.done_at = null;
    if ("deadline" in body && t.status === "overdue" && t.deadline && t.deadline >= new Date().toISOString().slice(0, 10)) {
      t.status = "in_progress";
    }
    refreshOverdue();
    return HttpResponse.json(withTitle(t));
  })),

  http.delete(A("/tasks/:id"), authed(({ params }) => {
    db.tasks = db.tasks.filter((t) => t.id !== num(params.id));
    return new HttpResponse(null, { status: 204 });
  })),

  /* ---------------- notifications ---------------- */
  http.get(A("/notifications"), authed(({ request }) => {
    tickProcessing();
    const unread = new URL(request.url).searchParams.get("unread") === "1";
    const mine = db.notifications.filter((n) => n.user_id === db.sessionUserId && (!unread || !n.read_at));
    return HttpResponse.json(mine.slice(0, 50).map(notificationOut));
  })),
  http.get(A("/notifications/unread-count"), authed(() => {
    const unread = db.notifications.filter((n) => n.user_id === db.sessionUserId && !n.read_at).length;
    return HttpResponse.json({ unread });
  })),
  http.post(A("/notifications/read-all"), authed(() => {
    for (const n of db.notifications) if (n.user_id === db.sessionUserId && !n.read_at) n.read_at = now();
    return HttpResponse.json({ unread: 0 });
  })),
  http.post(A("/notifications/:id/read"), authed(({ params }) => {
    const n = db.notifications.find((x) => x.id === num(params.id) && x.user_id === db.sessionUserId);
    if (!n) return detail(404, "Notification not found");
    if (!n.read_at) n.read_at = now();
    return HttpResponse.json(notificationOut(n));
  })),
];
