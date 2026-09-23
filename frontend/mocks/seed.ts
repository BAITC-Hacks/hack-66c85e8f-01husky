/**
 * Demo fixtures mirroring spec §6/§7 shapes. Dates are relative to "today" so
 * deadlines, overdue and due-soon states always look alive during a demo.
 */
import type {
  Direction,
  Meeting,
  Notification,
  Participant,
  Segment,
  SpeakerMapping,
  Task,
  User,
} from "@/lib/api/types";

const DAY = 86_400_000;
export const iso = (d: Date) => d.toISOString().slice(0, 10);
export const daysFromNow = (n: number) => iso(new Date(Date.now() + n * DAY));
const ts = (n: number) => new Date(Date.now() + n * DAY).toISOString();

function nextFriday(from: Date) {
  const d = new Date(from);
  d.setDate(d.getDate() + ((5 - d.getDay() + 7) % 7 || 7));
  return iso(d);
}
function endOfMonth(from: Date) {
  return iso(new Date(from.getFullYear(), from.getMonth() + 1, 0));
}

export const MODEL_INFO = {
  stt: "faster-whisper large-v3-turbo",
  diarization: "pyannote 3.1",
  voiceprint: "speechbrain ECAPA",
  llm: "qwen3:14b · ollama",
};

export const seedUsers: (User & { password: string })[] = [
  {
    id: 1,
    email: "admin@kenes.ai",
    password: "admin",
    name: "Айгерим Жумабаева",
    role: "admin",
    locale: "ru",
    created_at: ts(-60),
  },
];

export const seedParticipants: Participant[] = [
  { id: 1, name: "Айбек Нуров", email: "a.nurov@kenes.ai", position: "Директор по ИТ", user_id: null, has_voiceprint: true, created_at: ts(-50) },
  { id: 2, name: "Динара Касымова", email: "d.kassymova@kenes.ai", position: "Главный бухгалтер", user_id: null, has_voiceprint: false, created_at: ts(-50) },
  { id: 3, name: "Ержан Абенов", email: "e.abenov@kenes.ai", position: "Юрист", user_id: null, has_voiceprint: true, created_at: ts(-50) },
  { id: 4, name: "Мария Ким", email: "m.kim@kenes.ai", position: "HR-менеджер", user_id: null, has_voiceprint: false, created_at: ts(-45) },
  { id: 5, name: "Тимур Ахметов", email: "t.akhmetov@kenes.ai", position: "Отдел закупок", user_id: null, has_voiceprint: false, created_at: ts(-40) },
  { id: 6, name: "Айгерим Жумабаева", email: "admin@kenes.ai", position: "Секретарь правления", user_id: 1, has_voiceprint: true, created_at: ts(-60) },
];

export const seedDirections: Direction[] = [
  "Финансы",
  "Кадры",
  "ИТ",
  "Юридическое",
  "Закупки",
  "Производство",
  "Другое",
].map((name, i) => ({ id: i + 1, name, is_active: true }));

const DIR = Object.fromEntries(seedDirections.map((d) => [d.name, d.id]));

/* ---------- template transcript (also reused for freshly "processed" meetings) ---------- */

type Seg = [number, number, string, Segment["lang"], string];
export const TEMPLATE_SEGMENTS: Seg[] = [
  [0, 9.4, "SPEAKER_00", "ru", "Коллеги, добрый день. Начинаем планёрку по бюджету четвёртого квартала и закупкам."],
  [9.4, 21, "SPEAKER_00", "mixed", "Бүгін үш мәселе бар: бюджет, серверлер және келісімшарттар. Давайте по порядку."],
  [21, 38, "SPEAKER_01", "ru", "По бюджету: мы выбрали восемьдесят два процента лимита. Остаток на ИТ — около сорока миллионов тенге."],
  [38, 49, "SPEAKER_00", "ru", "Динара, подготовьте, пожалуйста, сводку по остаткам по всем направлениям до пятницы."],
  [49, 55, "SPEAKER_01", "ru", "Хорошо, до пятницы сделаю."],
  [55, 72, "SPEAKER_03", "mixed", "Серверлер бойынша: текущие стойки загружены на девяносто процентов. Нам срочно нужно расширение, иначе сервис протоколов не встанет в контур."],
  [72, 86, "SPEAKER_00", "kk", "Айбек, техникалық тапсырманы ертеңге дейін дайында, жедел."],
  [86, 92, "SPEAKER_03", "kk", "Жарайды, ертең беремін."],
  [92, 110, "SPEAKER_02", "ru", "По закупкам: тендер на серверное оборудование можно объявить после ТЗ. Срок размещения — около недели."],
  [110, 122, "SPEAKER_00", "ru", "Тимур, объявите тендер в течение недели после получения ТЗ от Айбека."],
  [122, 138, "SPEAKER_02", "mixed", "Понял. Келісімшарт жобасын заңгерге жіберемін, Ержан посмотрит."],
  [138, 152, "SPEAKER_00", "ru", "Ержан, проверьте договор до конца месяца. Контакт поставщика: +7 (•••) •••-••-45."],
  [152, 170, "SPEAKER_01", "kk", "Айдың соңына дейін қаржы есебін де жаңарту керек, мен өзім жасаймын."],
  [170, 184, "SPEAKER_00", "ru", "Отлично. Итоги: сводка — Динара, ТЗ — Айбек, тендер — Тимур, договор — Ержан. Всем спасибо."],
];

export const TEMPLATE_SUMMARY = `## Тема
Бюджет IV квартала, расширение серверной инфраструктуры и закупки.

## Решения
- Освоение бюджета — **82 %** лимита; остаток по ИТ ≈ 40 млн ₸.
- Расширение серверных стоек признано **срочным**.
- Тендер на оборудование объявляется после готовности ТЗ.

## Поручения
1. Динара Касымова — сводка по остаткам бюджета (до пятницы).
2. Айбек Нуров — ТЗ на расширение серверов (завтра, срочно).
3. Тимур — тендер на серверное оборудование (в течение недели).
4. Ержан Абенов — проверка договора с поставщиком (до конца месяца).

## Открытые вопросы
- Источник финансирования, если расширение превысит остаток по ИТ.`;

export function buildSegments(idBase: number): Segment[] {
  return TEMPLATE_SEGMENTS.map(([start, end, speaker, lang, text], idx) => ({
    id: idBase + idx,
    idx,
    start,
    end,
    speaker,
    text,
    lang,
  }));
}

export function buildTasks(meetingId: number, meetingDate: string, idBase: number, speakerToParticipant: (i: number) => number | null): Task[] {
  const md = new Date(meetingDate);
  const plus = (n: number) => iso(new Date(md.getTime() + n * DAY));
  const base = {
    meeting_id: meetingId,
    status: "draft" as const,
    sed_ref: null,
    created_at: ts(0),
    updated_at: ts(0),
    done_at: null,
  };
  return [
    {
      ...base,
      id: idBase,
      assignee_participant_id: speakerToParticipant(1) ?? 2,
      assignee_name: "Динара",
      text: "Подготовить сводку по остаткам бюджета по всем направлениям",
      deadline: nextFriday(md),
      deadline_raw: "до пятницы",
      urgency: "normal",
      direction_id: DIR["Финансы"],
      quote: "подготовьте, пожалуйста, сводку по остаткам по всем направлениям до пятницы",
      segment_idx: 3,
      confidence: 0.93,
    },
    {
      ...base,
      id: idBase + 1,
      assignee_participant_id: speakerToParticipant(3) ?? 1,
      assignee_name: "Айбек",
      text: "Подготовить техническое задание на расширение серверных мощностей",
      deadline: plus(1),
      deadline_raw: "ертеңге дейін",
      urgency: "critical",
      direction_id: DIR["ИТ"],
      quote: "техникалық тапсырманы ертеңге дейін дайында, жедел",
      segment_idx: 6,
      confidence: 0.88,
    },
    {
      ...base,
      id: idBase + 2,
      assignee_participant_id: null,
      assignee_name: "Тимур",
      text: "Объявить тендер на серверное оборудование после получения ТЗ",
      deadline: plus(7),
      deadline_raw: "в течение недели",
      urgency: "high",
      direction_id: DIR["Закупки"],
      quote: "объявите тендер в течение недели после получения ТЗ от Айбека",
      segment_idx: 9,
      confidence: 0.61,
    },
    {
      ...base,
      id: idBase + 3,
      assignee_participant_id: 3,
      assignee_name: "Ержан",
      text: "Проверить проект договора с поставщиком оборудования",
      deadline: endOfMonth(md),
      deadline_raw: "до конца месяца",
      urgency: "normal",
      direction_id: DIR["Юридическое"],
      quote: "проверьте договор до конца месяца",
      segment_idx: 11,
      confidence: 0.9,
    },
    {
      ...base,
      id: idBase + 4,
      assignee_participant_id: speakerToParticipant(1) ?? 2,
      assignee_name: "Динара",
      text: "Обновить финансовый отчёт",
      deadline: endOfMonth(md),
      deadline_raw: "айдың соңына дейін",
      urgency: "normal",
      direction_id: DIR["Финансы"],
      quote: "Айдың соңына дейін қаржы есебін де жаңарту керек",
      segment_idx: 12,
      confidence: 0.79,
    },
  ];
}

const meetingBase = {
  platform: null,
  has_audio: true,
  output_language: "ru" as const,
  progress_stage: null,
  progress_pct: null,
  error: null,
  sed_ref: null,
  created_by: 1,
  confirmed_at: null,
  model_info: MODEL_INFO,
};

export function seedMeetings(): Meeting[] {
  return [
    {
      ...meetingBase,
      id: 101,
      title: "Бюджет IV квартала и закупки",
      meeting_date: daysFromNow(-1),
      source: "upload",
      duration_sec: 184,
      status: "draft",
      summary: TEMPLATE_SUMMARY,
      language_stats: { ru: 0.57, kk: 0.21, mixed: 0.22 },
      created_at: ts(-1),
    },
    {
      ...meetingBase,
      id: 102,
      title: "Совет директоров: стратегия 2027",
      meeting_date: daysFromNow(0),
      source: "live",
      duration_sec: 2710,
      status: "processing",
      progress_stage: "stt",
      progress_pct: 0.05,
      summary: null,
      language_stats: null,
      created_at: ts(0),
    },
    {
      ...meetingBase,
      id: 103,
      title: "Планёрка ИТ-департамента",
      meeting_date: daysFromNow(-6),
      source: "bot",
      platform: "meet",
      duration_sec: 1325,
      status: "confirmed",
      summary:
        "## Тема\nМиграция почты и портал СЭД.\n\n## Решения\n- Миграция почты — до конца месяца.\n- Портал СЭД переводим на SSO.\n\n## Открытые вопросы\n- Лицензии на резервное копирование.",
      language_stats: { ru: 0.71, kk: 0.12, mixed: 0.17 },
      sed_ref: "SED-2026-000118",
      created_at: ts(-6),
      confirmed_at: ts(-5),
    },
    {
      ...meetingBase,
      id: 104,
      title: "Кадровый комитет",
      meeting_date: daysFromNow(-14),
      source: "upload",
      duration_sec: 2104,
      status: "confirmed",
      output_language: "kk",
      summary: "## Тақырып\nІшкі оқыту бағдарламасы және вакансиялар.\n\n## Шешімдер\n- Екі вакансия ашылады.\n- Оқыту бағдарламасы қазанда басталады.",
      language_stats: { ru: 0.34, kk: 0.52, mixed: 0.14 },
      sed_ref: "SED-2026-000097",
      created_at: ts(-14),
      confirmed_at: ts(-13),
    },
    {
      ...meetingBase,
      id: 105,
      title: "Созвон с подрядчиком «ТехСтрой»",
      meeting_date: daysFromNow(-2),
      source: "bot",
      platform: "zoom",
      has_audio: false,
      duration_sec: null,
      status: "failed",
      summary: null,
      language_stats: null,
      model_info: null,
      error: "Бот не был допущен в конференцию: истекло время ожидания в лобби (120 с).",
      created_at: ts(-2),
    },
  ];
}

export const seedMeetingParticipants: Record<number, number[]> = {
  101: [6, 2, 5, 1, 3],
  102: [6, 1, 2, 3, 4, 5],
  103: [6, 1, 3],
  104: [6, 4, 2],
  105: [6, 1, 5],
};

export const seedSpeakerMaps: Record<number, SpeakerMapping[]> = {
  101: [
    { speaker: "SPEAKER_00", participant_id: 6, source: "voiceprint", confidence: 0.91 },
    { speaker: "SPEAKER_01", participant_id: 2, source: "llm", confidence: 0.74 },
    { speaker: "SPEAKER_02", participant_id: null, source: "none", confidence: 0 },
    { speaker: "SPEAKER_03", participant_id: 1, source: "voiceprint", confidence: 0.83 },
  ],
  103: [
    { speaker: "SPEAKER_00", participant_id: 6, source: "voiceprint", confidence: 0.94 },
    { speaker: "SPEAKER_01", participant_id: 1, source: "voiceprint", confidence: 0.88 },
    { speaker: "SPEAKER_02", participant_id: 3, source: "manual", confidence: 1 },
  ],
};

export function seedSegments(): Record<number, Segment[]> {
  const it: Seg[] = [
    [0, 14, "SPEAKER_00", "ru", "Начинаем. Первый вопрос — миграция почты на внутренний сервер."],
    [14, 36, "SPEAKER_01", "mixed", "Пошта көші-қоны дайын, осталось перенести архивы бухгалтерии."],
    [36, 48, "SPEAKER_00", "ru", "Айбек, завершите миграцию до конца месяца, пожалуйста."],
    [48, 70, "SPEAKER_02", "ru", "По порталу СЭД: юридически SSO допустим, согласование я подготовил."],
    [70, 84, "SPEAKER_00", "kk", "Жақсы. Ержан, келісімді екі күнде жібер."],
    [84, 96, "SPEAKER_00", "ru", "Я сама подготовлю сводку по лицензиям к следующей планёрке."],
  ];
  const mk = (rows: Seg[], base: number) =>
    rows.map(([start, end, speaker, lang, text], idx) => ({ id: base + idx, idx, start, end, speaker, text, lang }));
  return { 101: buildSegments(1000), 103: mk(it, 2000), 104: [] };
}

export function seedTasks(): Task[] {
  const done = {
    sed_ref: null,
    created_at: ts(-5),
    updated_at: ts(-1),
  };
  return [
    ...buildTasks(101, daysFromNow(-1), 1, () => null),
    {
      ...done,
      id: 20,
      meeting_id: 103,
      assignee_participant_id: 1,
      assignee_name: "Айбек",
      text: "Завершить миграцию почты, включая архивы бухгалтерии",
      deadline: daysFromNow(3),
      deadline_raw: "до конца месяца",
      urgency: "high",
      direction_id: DIR["ИТ"],
      quote: "Айбек, завершите миграцию до конца месяца, пожалуйста.",
      segment_idx: 2,
      confidence: 0.95,
      status: "in_progress",
      done_at: null,
    },
    {
      ...done,
      id: 21,
      meeting_id: 103,
      assignee_participant_id: 3,
      assignee_name: "Ержан",
      text: "Направить согласование по SSO для портала СЭД",
      deadline: daysFromNow(-2),
      deadline_raw: "екі күнде",
      urgency: "normal",
      direction_id: DIR["Юридическое"],
      quote: "Ержан, келісімді екі күнде жібер.",
      segment_idx: 4,
      confidence: 0.86,
      status: "overdue",
      done_at: null,
    },
    {
      ...done,
      id: 22,
      meeting_id: 103,
      assignee_participant_id: 6,
      assignee_name: "Айгерим",
      text: "Подготовить сводку по лицензиям резервного копирования",
      deadline: daysFromNow(1),
      deadline_raw: "к следующей планёрке",
      urgency: "normal",
      direction_id: DIR["ИТ"],
      quote: "Я сама подготовлю сводку по лицензиям к следующей планёрке.",
      segment_idx: 5,
      confidence: 0.9,
      status: "confirmed",
      done_at: null,
    },
    {
      ...done,
      id: 30,
      meeting_id: 104,
      assignee_participant_id: 4,
      assignee_name: "Мария",
      text: "Екі вакансия бойынша хабарландыру жариялау",
      deadline: daysFromNow(-8),
      deadline_raw: "бір аптада",
      urgency: "normal",
      direction_id: DIR["Кадры"],
      quote: "Мария, вакансияларды бір аптада жарияла.",
      segment_idx: 0,
      confidence: 0.92,
      status: "done",
      done_at: ts(-9),
    },
    {
      ...done,
      id: 31,
      meeting_id: 104,
      assignee_participant_id: 6,
      assignee_name: "Айгерим",
      text: "Согласовать программу внутреннего обучения",
      deadline: daysFromNow(9),
      deadline_raw: "қазан айының басына дейін",
      urgency: "low",
      direction_id: DIR["Кадры"],
      quote: "Оқыту бағдарламасын қазан айының басына дейін келісу керек.",
      segment_idx: 1,
      confidence: 0.81,
      status: "in_progress",
      done_at: null,
    },
    {
      ...done,
      id: 32,
      meeting_id: 104,
      assignee_participant_id: 2,
      assignee_name: "Динара",
      text: "Рассчитать фонд оплаты труда для новых вакансий",
      deadline: daysFromNow(-4),
      deadline_raw: "до двадцатого",
      urgency: "high",
      direction_id: DIR["Финансы"],
      quote: "Динара, посчитайте ФОТ до двадцатого.",
      segment_idx: 2,
      confidence: 0.89,
      status: "done",
      done_at: ts(-5),
    },
  ];
}

export function seedNotifications(): Notification[] {
  return [
    {
      id: 1,
      user_id: 1,
      task_id: 22,
      meeting_id: 103,
      kind: "due_soon",
      title: "Срок завтра",
      body: "Подготовить сводку по лицензиям резервного копирования",
      read_at: null,
      created_at: ts(-0.1),
    },
    {
      id: 2,
      user_id: 1,
      task_id: 21,
      meeting_id: 103,
      kind: "overdue",
      title: "Поручение просрочено",
      body: "Ержан Абенов · Направить согласование по SSO для портала СЭД",
      read_at: null,
      created_at: ts(-0.5),
    },
    {
      id: 3,
      user_id: 1,
      task_id: null,
      meeting_id: 101,
      kind: "protocol_ready",
      title: "Черновик протокола готов",
      body: "Бюджет IV квартала и закупки — 5 поручений ждут проверки",
      read_at: null,
      created_at: ts(-0.9),
    },
    {
      id: 4,
      user_id: 1,
      task_id: 31,
      meeting_id: 104,
      kind: "assigned",
      title: "Вам назначено поручение",
      body: "Согласовать программу внутреннего обучения",
      read_at: ts(-12),
      created_at: ts(-13),
    },
  ];
}
