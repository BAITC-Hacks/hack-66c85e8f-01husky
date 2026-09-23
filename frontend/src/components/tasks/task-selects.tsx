"use client";

import { useTranslations } from "next-intl";
import { UrgencyMark } from "@/components/common/badges";
import { TaskStatusBadge } from "@/components/common/badges";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Direction, Participant, TaskStatus, Urgency } from "@/lib/api/types";
import { TASK_STATUSES, URGENCY_ORDER } from "@/lib/format";
import { cn } from "@/lib/utils";

const NONE = "__none";
const trigger = "h-8 w-full min-w-0 text-[13px]";

export function AssigneeSelect({
  value,
  fallbackName,
  participants,
  onChange,
  disabled,
  className,
}: {
  value: number | null;
  fallbackName?: string;
  participants: Participant[];
  onChange: (id: number | null) => void;
  disabled?: boolean;
  className?: string;
}) {
  const t = useTranslations("taskTable");
  return (
    <Select disabled={disabled} value={value ? String(value) : NONE} onValueChange={(v) => onChange(v === NONE ? null : Number(v))}>
      <SelectTrigger className={cn(trigger, !value && "border-dashed border-coral/50 text-coral", className)}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={NONE}>
          {fallbackName ? `${fallbackName} · ${t("unmatched")}` : "—"}
        </SelectItem>
        {participants.map((p) => (
          <SelectItem key={p.id} value={String(p.id)}>
            {p.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function UrgencySelect({ value, onChange, disabled }: { value: Urgency; onChange: (u: Urgency) => void; disabled?: boolean }) {
  return (
    <Select disabled={disabled} value={value} onValueChange={(v) => onChange(v as Urgency)}>
      <SelectTrigger className={trigger}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {URGENCY_ORDER.map((u) => (
          <SelectItem key={u} value={u}>
            <UrgencyMark urgency={u} />
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function DirectionSelect({
  value,
  directions,
  onChange,
  disabled,
}: {
  value: number;
  directions: Direction[];
  onChange: (id: number) => void;
  disabled?: boolean;
}) {
  return (
    <Select disabled={disabled} value={String(value)} onValueChange={(v) => onChange(Number(v))}>
      <SelectTrigger className={trigger}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {directions
          .filter((d) => d.is_active || d.id === value)
          .map((d) => (
            <SelectItem key={d.id} value={String(d.id)}>
              {d.name}
            </SelectItem>
          ))}
      </SelectContent>
    </Select>
  );
}

/** Status transitions allowed from the dashboard (spec §6). */
export function StatusSelect({
  value,
  onChange,
  disabled,
}: {
  value: TaskStatus;
  onChange: (s: TaskStatus) => void;
  disabled?: boolean;
}) {
  const options: TaskStatus[] =
    value === "draft" ? ["draft"] : value === "overdue" ? ["overdue", "in_progress", "done"] : ["confirmed", "in_progress", "done"];
  return (
    <Select disabled={disabled || value === "draft"} value={value} onValueChange={(v) => onChange(v as TaskStatus)}>
      <SelectTrigger className="h-8 w-[9.5rem] border-transparent bg-transparent px-1 shadow-none hover:border-border">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {TASK_STATUSES.filter((s) => options.includes(s)).map((s) => (
          <SelectItem key={s} value={s}>
            <TaskStatusBadge status={s} />
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
