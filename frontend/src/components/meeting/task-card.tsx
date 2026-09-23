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
        "group bg-card shadow-soft relative rounded-xl border p-4 transition-shadow",
        highlighted && "ring-primary ring-2",
        low && "border-l-coral/70 border-l-4",
      )}
    >
      <div className="flex items-start gap-3">
        <span className="text-muted-foreground tabular mt-1 font-mono text-[11px]">
          {String(index + 1).padStart(2, "0")}
        </span>
        <div className="min-w-0 flex-1">
          <textarea
            value={text}
            disabled={readOnly}
            rows={1}
            onChange={(e) => setText(e.target.value)}
            onBlur={() => text.trim() && text !== task.text && save({ text: text.trim() })}
            className="font-heading focus:bg-muted/50 focus:ring-ring/30 field-sizing-content w-full resize-none rounded-sm bg-transparent text-[15px] leading-snug font-medium outline-none focus:ring-2 disabled:cursor-default"
          />
          {task.quote && (
            <button
              onClick={onQuote}
              className="text-muted-foreground hover:text-foreground mt-1.5 flex w-full items-start gap-1.5 text-left text-xs transition-colors"
              title={t("showInTranscript")}
            >
              <Quote className="text-primary mt-0.5 size-3 shrink-0" />
              <span className="decoration-primary/40 line-clamp-2 italic underline decoration-dotted underline-offset-4">
                {task.quote}
              </span>
            </button>
          )}
        </div>
        {!readOnly && (
          <Button
            variant="ghost"
            size="icon-sm"
            className="opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
            onClick={() =>
              del.mutate(
                { id: task.id, meetingId: task.meeting_id },
                { onSuccess: () => toast(t("deleted")) },
              )
            }
            aria-label="delete"
          >
            <Trash2 className="text-coral" />
          </Button>
        )}
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 min-[420px]:grid-cols-2 sm:pl-7">
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

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs sm:pl-7">
        <TaskStatusBadge status={task.status} />
        {task.deadline_raw && <span className="text-muted-foreground italic">«{task.deadline_raw}»</span>}
        <span className="text-muted-foreground ml-auto inline-flex items-center gap-1.5">
          {low && <AlertTriangle className="text-coral size-3" aria-label={t("lowConfidence")} />}
          {task.segment_idx < 0 ? t("manual") : <ConfidenceMeter value={task.confidence} />}
        </span>
      </div>
    </li>
  );
}
