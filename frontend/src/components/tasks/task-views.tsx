"use client";

import { ArrowRightLeft, Lock, Quote } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { TaskStatusBadge, UrgencyMark } from "@/components/common/badges";
import { DeadlineLabel, ParticipantAvatar } from "@/components/common/bits";
import { StatusSelect } from "@/components/tasks/task-selects";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Task, TaskStatus } from "@/lib/api/types";
import {
  allowedStatuses,
  DEADLINE_BUCKETS,
  deadlineBucket,
  deadlineInfo,
  type DeadlineBucket,
} from "@/lib/format";
import { cn } from "@/lib/utils";

export type TaskView = "list" | "board" | "agenda";
export const TASK_VIEWS: TaskView[] = ["list", "board", "agenda"];

/** What every task view needs from the page: rows plus name lookups and the status mutation. */
export interface TaskViewProps {
  tasks: Task[];
  assigneeName: (task: Task) => { name: string; matched: boolean };
  directionName: (task: Task) => string;
  onStatus: (task: Task, status: TaskStatus, opts?: { onError?: () => void }) => void;
  busy?: boolean;
}

function MeetingLink({ task, className }: { task: Task; className?: string }) {
  return (
    <Link
      href={`/meetings/${task.meeting_id}`}
      className={cn(
        "text-muted-foreground hover:text-primary block truncate text-xs hover:underline",
        className,
      )}
    >
      № {task.meeting_id} · {task.meeting_title}
    </Link>
  );
}

function Assignee({ name, matched }: { name: string; matched: boolean }) {
  return (
    <span className="inline-flex min-w-0 items-center gap-2">
      <ParticipantAvatar name={name} size="sm" />
      <span className={cn("truncate text-sm", !matched && "text-coral")}>{name}</span>
    </span>
  );
}

/* ───────────────────────── Board (kanban) ───────────────────────── */

const COLUMNS: { status: TaskStatus; tone: string }[] = [
  { status: "draft", tone: "var(--muted-foreground)" },
  { status: "confirmed", tone: "var(--brand)" },
  { status: "in_progress", tone: "var(--sun)" },
  { status: "overdue", tone: "var(--coral)" },
  { status: "done", tone: "var(--mint)" },
];

/** Optimistic move: applies only while the server still reports `from`, so it expires on its own. */
type Move = { from: TaskStatus; to: TaskStatus };

export function TaskBoard({ tasks, assigneeName, onStatus }: TaskViewProps) {
  const t = useTranslations("tasks.board");
  const tst = useTranslations("taskStatus");
  const [moves, setMoves] = useState<Record<number, Move>>({});
  const [dragging, setDragging] = useState<Task | null>(null);
  const [over, setOver] = useState<TaskStatus | null>(null);

  const statusOf = (task: Task) => {
    const m = moves[task.id];
    return m && m.from === task.status ? m.to : task.status;
  };
  const canDrop = (task: Task | null, to: TaskStatus) =>
    !!task && statusOf(task) !== to && allowedStatuses(statusOf(task)).includes(to);

  const move = (task: Task, to: TaskStatus) => {
    const from = task.status;
    if (!canDrop(task, to)) return;
    setMoves((m) => ({ ...m, [task.id]: { from, to } }));
    onStatus(task, to, {
      onError: () =>
        setMoves((m) => {
          const rest = { ...m };
          delete rest[task.id];
          return rest;
        }),
    });
  };

  return (
    <div className="-mx-4 overflow-x-auto px-4 pb-2 sm:-mx-6 sm:px-6 xl:mx-0 xl:overflow-visible xl:px-0">
      <div className="flex snap-x snap-mandatory gap-3 xl:grid xl:grid-cols-5">
        {COLUMNS.map(({ status, tone }) => {
          const items = tasks.filter((task) => statusOf(task) === status);
          const droppable = canDrop(dragging, status);
          const dimmed = !!dragging && !droppable && statusOf(dragging) !== status;
          return (
            <section
              key={status}
              aria-label={tst(status)}
              onDragOver={(e) => {
                if (!droppable) return;
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
                if (over !== status) setOver(status);
              }}
              onDragLeave={(e) => {
                if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOver(null);
              }}
              onDrop={(e) => {
                e.preventDefault();
                if (dragging) move(dragging, status);
                setOver(null);
                setDragging(null);
              }}
              className={cn(
                "bg-muted/40 flex w-[80vw] max-w-[19rem] shrink-0 snap-start flex-col rounded-xl border p-2 transition-all sm:w-72 xl:w-auto xl:max-w-none xl:min-w-0",
                dimmed && "opacity-45",
                droppable && "border-dashed",
                over === status && "bg-brand-soft ring-2",
              )}
              style={{ ["--tw-ring-color" as string]: tone }}
            >
              <header className="flex items-center gap-2 px-1.5 pt-1 pb-2.5">
                <span className="size-2 rounded-full" style={{ background: tone }} />
                <h2 className="truncate text-sm font-semibold">{tst(status)}</h2>
                <span className="text-muted-foreground tabular text-xs">{items.length}</span>
                {status === "draft" && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Lock
                        className="text-muted-foreground ml-auto size-3.5"
                        aria-label={t("draftLocked")}
                      />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-60">{t("draftLocked")}</TooltipContent>
                  </Tooltip>
                )}
              </header>
              <ul className="flex min-h-24 flex-1 flex-col gap-2">
                {items.map((task) => {
                  const current = statusOf(task);
                  const targets = allowedStatuses(current).filter((s) => s !== current);
                  const who = assigneeName(task);
                  const tone = deadlineInfo(task.deadline, current).tone;
                  return (
                    <li
                      key={task.id}
                      draggable={targets.length > 0}
                      onDragStart={(e) => {
                        e.dataTransfer.effectAllowed = "move";
                        e.dataTransfer.setData("text/plain", String(task.id));
                        setDragging(task);
                      }}
                      onDragEnd={() => {
                        setDragging(null);
                        setOver(null);
                      }}
                      className={cn(
                        "group bg-card shadow-soft hover:shadow-lift rounded-lg border p-3 transition-shadow",
                        targets.length > 0 && "cursor-grab active:cursor-grabbing",
                        dragging?.id === task.id && "opacity-50",
                        tone === "overdue" && current !== "overdue" && "border-coral/40",
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm leading-snug font-medium">{task.text}</p>
                        <UrgencyMark urgency={task.urgency} withLabel={false} />
                      </div>
                      <MeetingLink task={task} className="mt-1" />
                      <div className="mt-3 flex items-center justify-between gap-2">
                        <Assignee {...who} />
                        {targets.length > 0 && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="text-muted-foreground size-7 shrink-0"
                                aria-label={t("moveTo")}
                              >
                                <ArrowRightLeft className="size-3.5" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuLabel className="text-muted-foreground text-xs">
                                {t("moveTo")}
                              </DropdownMenuLabel>
                              {targets.map((s) => (
                                <DropdownMenuItem key={s} onSelect={() => move(task, s)}>
                                  <TaskStatusBadge status={s} />
                                </DropdownMenuItem>
                              ))}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
                      </div>
                      <div className="mt-2 border-t pt-2">
                        <DeadlineLabel deadline={task.deadline} status={current} />
                      </div>
                    </li>
                  );
                })}
                {items.length === 0 && (
                  <li className="text-muted-foreground flex flex-1 items-center justify-center rounded-lg border border-dashed px-3 py-6 text-center text-xs">
                    {droppable ? t("dropHere") : t("emptyColumn")}
                  </li>
                )}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}

/* ───────────────────────── Agenda (by deadline) ───────────────────────── */

const BUCKET_TONE: Record<DeadlineBucket, string> = {
  overdue: "var(--coral)",
  today: "var(--sun)",
  tomorrow: "var(--sun)",
  week: "var(--brand)",
  later: "var(--brand)",
  none: "var(--muted-foreground)",
  done: "var(--mint)",
};

export function TaskAgenda({ tasks, assigneeName, directionName, onStatus, busy }: TaskViewProps) {
  const t = useTranslations("tasks.agenda");
  const groups = DEADLINE_BUCKETS.map((bucket) => ({
    bucket,
    items: tasks.filter((task) => deadlineBucket(task.deadline, task.status) === bucket),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="grid gap-6">
      {groups.map(({ bucket, items }) => (
        <section key={bucket} aria-label={t(bucket)}>
          <header className="mb-2 flex items-center gap-2 px-1">
            <span className="size-2 rounded-full" style={{ background: BUCKET_TONE[bucket] }} />
            <h2 className="font-heading text-lg font-bold">{t(bucket)}</h2>
            <span className="text-muted-foreground tabular text-sm">{items.length}</span>
          </header>
          <ul
            className={cn(
              "bg-card shadow-soft divide-y overflow-hidden rounded-xl border",
              bucket === "overdue" && "border-coral/40",
              bucket === "done" && "opacity-80",
            )}
          >
            {items.map((task) => (
              <li
                key={task.id}
                className="grid gap-x-4 gap-y-2 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_11rem_8rem_auto] sm:items-center"
              >
                <div className="flex min-w-0 items-start gap-3">
                  <span className="mt-1">
                    <UrgencyMark urgency={task.urgency} withLabel={false} />
                  </span>
                  <div className="min-w-0">
                    <p className={cn("leading-snug font-medium", task.status === "done" && "line-through")}>
                      {task.text}
                      {task.quote && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Quote className="text-primary ml-1.5 inline size-3 align-baseline" />
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs italic">«{task.quote}»</TooltipContent>
                        </Tooltip>
                      )}
                    </p>
                    <MeetingLink task={task} className="mt-0.5" />
                    <p className="text-muted-foreground mt-0.5 truncate text-xs">{directionName(task)}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between gap-3 pl-7 sm:contents">
                  <Assignee {...assigneeName(task)} />
                  <DeadlineLabel deadline={task.deadline} status={task.status} />
                </div>
                <div className="pl-7 sm:pl-0">
                  <StatusSelect
                    value={task.status}
                    disabled={busy}
                    onChange={(status) => onStatus(task, status)}
                  />
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
