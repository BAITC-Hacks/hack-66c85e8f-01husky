"use client";

import { AlertTriangle, Quote, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ConfidenceMeter } from "@/components/common/bits";
import { TaskStatusBadge } from "@/components/common/badges";
import { DatePicker } from "@/components/common/date-picker";
import { AssigneeSelect, DirectionSelect, UrgencySelect } from "@/components/tasks/task-selects";
import { Button } from "@/components/ui/button";
import { useDeleteTask, useUpdateTask } from "@/lib/api/queries/tasks";
import type { Direction, Participant, Task, TaskPatch } from "@/lib/api/types";
import { LOW_CONFIDENCE } from "@/lib/format";
import { cn } from "@/lib/utils";

export function TaskCard({
  task,
  index,
  participants,
  directions,
  readOnly,
  highlighted,
  onQuote,
}: {
  task: Task;
  index: number;
  participants: Participant[];
  directions: Direction[];
  readOnly: boolean;
  highlighted: boolean;
  onQuote: () => void;
}) {
  const t = useTranslations("taskTable");
  const update = useUpdateTask();
  const del = useDeleteTask();
  const [text, setText] = useState(task.text);
  useEffect(() => setText(task.text), [task.text]);

  const save = (patch: TaskPatch) =>
    update.mutate({ id: task.id, ...patch }, { onError: (e) => toast.error(e.message) });
  const low = task.confidence < LOW_CONFIDENCE;

  return (
    <li
      id={`task-${task.id}`}
      className={cn(
        "group relative rounded-lg border bg-card p-4 transition-shadow",
        highlighted && "ring-2 ring-gold",
        low && "border-l-4 border-l-brick/70",
      )}
    >
      <div className="flex items-start gap-3">
        <span className="mt-1 font-mono text-[11px] text-muted-foreground tabular">{String(index + 1).padStart(2, "0")}</span>
        <div className="min-w-0 flex-1">
          <textarea
            value={text}
            disabled={readOnly}
            rows={1}
            onChange={(e) => setText(e.target.value)}
            onBlur={() => text.trim() && text !== task.text && save({ text: text.trim() })}
            className="field-sizing-content w-full resize-none rounded-sm bg-transparent font-heading text-[15px] leading-snug font-medium outline-none focus:bg-muted/50 focus:ring-2 focus:ring-ring/30 disabled:cursor-default"
          />
          {task.quote && (
            <button
              onClick={onQuote}
              className="mt-1.5 flex w-full items-start gap-1.5 text-left text-xs text-muted-foreground transition-colors hover:text-foreground"
              title={t("showInTranscript")}
            >
              <Quote className="mt-0.5 size-3 shrink-0 text-gold" />
              <span className="line-clamp-2 italic underline decoration-gold/40 decoration-dotted underline-offset-4">{task.quote}</span>
            </button>
          )}
        </div>
        {!readOnly && (
          <Button
            variant="ghost"
            size="icon-sm"
            className="opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
            onClick={() =>
              del.mutate({ id: task.id, meetingId: task.meeting_id }, { onSuccess: () => toast(t("deleted")) })
            }
            aria-label="delete"
          >
            <Trash2 className="text-brick" />
          </Button>
        )}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 pl-7">
        <AssigneeSelect
          value={task.assignee_participant_id}
          fallbackName={task.assignee_name}
          participants={participants}
          onChange={(id) => save({ assignee_participant_id: id })}
          disabled={readOnly}
        />
        <DatePicker
          size="sm"
          value={task.deadline}
          clearable={!readOnly}
          onChange={(d) => save({ deadline: d })}
          className="w-full text-[13px]"
        />
        <UrgencySelect value={task.urgency} onChange={(u) => save({ urgency: u })} disabled={readOnly} />
        <DirectionSelect
          value={task.direction_id}
          directions={directions}
          onChange={(id) => save({ direction_id: id })}
          disabled={readOnly}
        />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 pl-7 text-xs">
        <TaskStatusBadge status={task.status} />
        {task.deadline_raw && <span className="text-muted-foreground italic">«{task.deadline_raw}»</span>}
        <span className="ml-auto inline-flex items-center gap-1.5 text-muted-foreground">
          {low && <AlertTriangle className="size-3 text-brick" aria-label={t("lowConfidence")} />}
          {task.segment_idx < 0 ? t("manual") : <ConfidenceMeter value={task.confidence} />}
        </span>
      </div>
    </li>
  );
}
