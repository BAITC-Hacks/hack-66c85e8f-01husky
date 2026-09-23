import enum


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class Locale(str, enum.Enum):
    ru = "ru"
    kk = "kk"


class MeetingSource(str, enum.Enum):
    upload = "upload"
    live = "live"
    bot = "bot"


class MeetingStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    draft = "draft"
    confirmed = "confirmed"
    failed = "failed"


class SpeakerSource(str, enum.Enum):
    voiceprint = "voiceprint"
    llm = "llm"
    manual = "manual"
    none = "none"


class Urgency(str, enum.Enum):
    low = "low"
    normal = "normal"
    high = "high"
    critical = "critical"


class TaskStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    in_progress = "in_progress"
    done = "done"
    overdue = "overdue"


class NotificationKind(str, enum.Enum):
    assigned = "assigned"
    due_soon = "due_soon"
    overdue = "overdue"
    protocol_ready = "protocol_ready"


# Allowed manual status transitions (spec section 6). Beat sets overdue on its own.
TASK_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.draft: {TaskStatus.confirmed},
    TaskStatus.confirmed: {TaskStatus.in_progress, TaskStatus.done},
    TaskStatus.in_progress: {TaskStatus.done},
    TaskStatus.overdue: {TaskStatus.done, TaskStatus.in_progress},
    TaskStatus.done: {TaskStatus.in_progress},
}
