"use client";

import { useTranslations } from "next-intl";
import type { MeetingStatus, TaskStatus, Urgency } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const pill = "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap";

const MEETING_TONE: Record<MeetingStatus, string> = {
  uploaded: "border-border bg-muted text-muted-foreground",
  processing: "border-primary/30 bg-primary/10 text-primary",
  draft: "border-gold/40 bg-gold-soft text-foreground",
  confirmed: "border-sage/40 bg-sage/10 text-sage",
  failed: "border-brick/40 bg-brick/10 text-brick",
};

export function MeetingStatusBadge({ status, className }: { status: MeetingStatus; className?: string }) {
  const t = useTranslations("meetingStatus");
  return (
    <span className={cn(pill, MEETING_TONE[status], className)}>
      <span
        className={cn(
          "size-1.5 rounded-full bg-current",
          (status === "processing" || status === "uploaded") && "animate-rec",
        )}
      />
      {t(status)}
    </span>
  );
}

const TASK_TONE: Record<TaskStatus, string> = {
  draft: "border-dashed border-border text-muted-foreground",
  confirmed: "border-primary/30 bg-primary/10 text-primary",
  in_progress: "border-gold/40 bg-gold-soft text-foreground",
  done: "border-sage/40 bg-sage/10 text-sage",
  overdue: "border-brick/40 bg-brick/10 text-brick",
};

export function TaskStatusBadge({ status, className }: { status: TaskStatus; className?: string }) {
  const t = useTranslations("taskStatus");
  return <span className={cn(pill, TASK_TONE[status], className)}>{t(status)}</span>;
}

const URGENCY_LEVEL: Record<Urgency, number> = { low: 1, normal: 2, high: 3, critical: 4 };
const URGENCY_COLOR: Record<Urgency, string> = {
  low: "text-muted-foreground",
  normal: "text-primary",
  high: "text-gold",
  critical: "text-brick",
};

/** Four ascending bars, like signal strength. */
export function UrgencyMark({ urgency, withLabel = true }: { urgency: Urgency; withLabel?: boolean }) {
  const t = useTranslations("urgency");
  const lvl = URGENCY_LEVEL[urgency];
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", URGENCY_COLOR[urgency])}>
      <span className="inline-flex h-3 items-end gap-[2px]" aria-hidden>
        {[1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className={cn("w-[3px] rounded-[1px] bg-current", i > lvl && "opacity-20")}
            style={{ height: `${25 * i}%` }}
          />
        ))}
      </span>
      {withLabel && t(urgency)}
    </span>
  );
}
