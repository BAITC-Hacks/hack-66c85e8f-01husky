/**
 * MSW handlers for every endpoint in spec §7. Stateful: confirm, speakers,
 * task edits etc. mutate the mock db exactly as the backend is specified to.
 */
import { delay, http, HttpResponse, type PathParams } from "msw";
import type {
  Locale,
  Meeting,
  MeetingBotCreate,
  MeetingDetail,
  MeetingListItem,
  MeetingLiveCreate,
  MeetingPatch,
  Participant,
  SpeakerAssign,
  Task,
  TaskCreate,
  TaskPatch,
  TaskStatus,
  Urgency,
} from "@/lib/api/types";
import { db, isDueSoon, nextId, notify, now, refreshOverdue, save, startProcessing, tickProcessing } from "./db";
import { MINIMAL_PDF } from "./pdf";

const A = (p: string) => `*/api/v1${p}`;
const detail = (status: number, msg: string) => HttpResponse.json({ detail: msg }, { status });
const lag = () => delay(120 + Math.random() * 180);

function me() {
  return db.users.find((u) => u.id === db.sessionUserId) ?? null;
}
function publicUser(u: NonNullable<ReturnType<typeof me>>) {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { password, ...rest } = u;
  return rest;
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

function withTitle(t: Task): Task {
  return { ...t, meeting_title: meetingById(t.meeting_id)?.title };
}

function detailOf(m: Meeting): MeetingDetail {
  const pids = db.meetingParticipants[m.id] ?? [];
  return {
    meeting: m,
    participants: db.participants.filter((p) => pids.includes(p.id)),
    segments: db.segments[m.id] ?? [],
    speaker_map: db.speakerMaps[m.id] ?? [],
    tasks: db.tasks.filter((t) => t.meeting_id === m.id).map(withTitle),
    summary: m.summary,
  };
}

function newMeeting(fields: Partial<Meeting> & Pick<Meeting, "title" | "meeting_date" | "source">): Meeting {
  const m: Meeting = {
    id: nextId(),
    platform: null,
    has_audio: false,
    duration_sec: null,
    output_language: "ru",
    status: "uploaded",
    progress_stage: null,
    progress_pct: null,
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
    if (db.users.some((u) => u.email === body.email)) return detail(422, "Email already registered");
    const u = { id: nextId(), role: "user" as const, created_at: now(), ...body };
    db.users.push(u);
    const p = db.participants.find((x) => x.email === body.email);
    if (p) p.user_id = u.id;
    db.sessionUserId = u.id;
    save();
    return HttpResponse.json(publicUser(u));
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
  http.patch(A("/auth/me"), authed(async ({ request }) => {
    const body = (await request.json()) as { locale?: Locale; name?: string };
    Object.assign(me()!, body);
    return HttpResponse.json(publicUser(me()!));
  })),

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
    if (db.directions.some((d) => d.name.toLowerCase() === name.toLowerCase())) return detail(422, "Direction exists");
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
    const from = q.get("from");
    const to = q.get("to");
    const list: MeetingListItem[] = db.meetings
      .filter((m) => (!status || m.status === status) && (!from || m.meeting_date >= from) && (!to || m.meeting_date <= to))
      .map((m) => ({
        id: m.id,
        title: m.title,
        meeting_date: m.meeting_date,
        source: m.source,
        platform: m.platform,
        status: m.status,
        progress_pct: m.progress_pct,
        duration_sec: m.duration_sec,
        output_language: m.output_language,
        created_at: m.created_at,
        tasks_count: db.tasks.filter((t) => t.meeting_id === m.id).length,
        participants: db.participants
          .filter((p) => (db.meetingParticipants[m.id] ?? []).includes(p.id))
          .map((p) => ({ id: p.id, name: p.name })),
      }));
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
      has_audio: true,
    });
    db.meetingParticipants[m.id] = form.getAll("participant_ids").map(Number);
    startProcessing(m);
    return HttpResponse.json(m, { status: 201 });
  })),

  http.post(A("/meetings/live"), authed(async ({ request }) => {
    const body = (await request.json()) as MeetingLiveCreate;
    const m = newMeeting({ ...body, source: "live" });
    db.meetingParticipants[m.id] = body.participant_ids;
    return HttpResponse.json(m, { status: 201 });
  })),

  http.post(A("/meetings/bot"), authed(async ({ request }) => {
    const body = (await request.json()) as MeetingBotCreate;
    const m = newMeeting({
      title: body.title,
      meeting_date: body.meeting_date,
      source: "bot",
      platform: body.platform,
      status: "uploaded",
      progress_stage: "bot_joining",
    });
    db.meetingParticipants[m.id] = body.participant_ids;
    // pretend the bot records for a bit, then uploads
    db.processing[m.id] = Date.now() + 4_000;
    return HttpResponse.json(m, { status: 201 });
  })),

  http.post(A("/meetings/:id/audio"), authed(({ params }) => {
    const m = meetingById(num(params.id));
    if (!m) return detail(404, "Meeting not found");
    m.has_audio = true;
    startProcessing(m);
    return HttpResponse.json(m);
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
    Object.assign(m, (await request.json()) as MeetingPatch);
    return HttpResponse.json(m);
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
    if (!m.has_audio) return detail(422, "Audio was deleted, nothing to reprocess");
    m.confirmed_at = null;
    startProcessing(m);
    return HttpResponse.json(m);
  })),

  http.post(A("/meetings/:id/confirm"), authed(({ params }) => {
    const m = meetingById(num(params.id));
    if (!m) return detail(404, "Meeting not found");
    if (m.status !== "draft") return detail(422, "Only drafts can be confirmed");
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
    return HttpResponse.json(m);
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
    if (m.status !== "confirmed") return detail(422, "Confirm the protocol first");
    await delay(700);
    m.sed_ref = m.sed_ref ?? `SED-2026-${String(120 + (m.id % 1000)).padStart(6, "0")}`;
    for (const t of db.tasks) if (t.meeting_id === m.id) t.sed_ref = m.sed_ref;
    return HttpResponse.json({ sed_ref: m.sed_ref, outbox_path: `outbox/${m.id}/protocol.pdf` });
  })),

  http.delete(A("/meetings/:id/audio"), authed(({ params }) => {
    const m = meetingById(num(params.id));
    if (!m) return detail(404, "Meeting not found");
    m.has_audio = false;
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
    return HttpResponse.json({
      draft: c("draft"),
      confirmed: c("confirmed"),
      in_progress: c("in_progress"),
      done: c("done"),
      overdue: c("overdue"),
      due_soon: db.tasks.filter(isDueSoon).length,
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
    const t: Task = {
      id: nextId(),
      meeting_id: body.meeting_id,
      assignee_participant_id: body.assignee_participant_id ?? null,
      assignee_name: body.assignee_name ?? p?.name ?? "",
      text: body.text,
      deadline: body.deadline ?? null,
      deadline_raw: null,
      urgency: (body.urgency ?? "normal") as Urgency,
      direction_id: body.direction_id ?? db.directions.find((d) => d.name === "Другое")!.id,
      quote: "",
      segment_idx: -1,
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
    return HttpResponse.json(mine.slice(0, 50));
  })),
  http.post(A("/notifications/read-all"), authed(() => {
    for (const n of db.notifications) if (n.user_id === db.sessionUserId && !n.read_at) n.read_at = now();
    return new HttpResponse(null, { status: 204 });
  })),
  http.post(A("/notifications/:id/read"), authed(({ params }) => {
    const n = db.notifications.find((x) => x.id === num(params.id));
    if (n && !n.read_at) n.read_at = now();
    return new HttpResponse(null, { status: 204 });
  })),
];
