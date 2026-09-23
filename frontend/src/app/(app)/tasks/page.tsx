"use client";

import { AlarmClock, CheckCircle2, CircleDashed, FilterX, Quote, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { UrgencyMark } from "@/components/common/badges";
import { DeadlineLabel, EmptyState, PageHeader, ParticipantAvatar } from "@/components/common/bits";
import { StatusSelect } from "@/components/tasks/task-selects";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useDirections } from "@/lib/api/queries/directions";
import { useMeetings } from "@/lib/api/queries/meetings";
import { useParticipants } from "@/lib/api/queries/participants";
import { useTasks, useTaskStats, useUpdateTask } from "@/lib/api/queries/tasks";
import type { TaskFilters, TaskStats, TaskStatus, Urgency } from "@/lib/api/types";
import { deadlineInfo, TASK_STATUSES, URGENCY_ORDER } from "@/lib/format";
import { cn } from "@/lib/utils";

const ALL = "__all";
type CounterKey = "in_progress" | "overdue" | "done" | "due_soon";

const COUNTERS: { key: CounterKey; icon: typeof AlarmClock; tone: string }[] = [
  { key: "in_progress", icon: CircleDashed, tone: "var(--brand)" },
  { key: "overdue", icon: TriangleAlert, tone: "var(--coral)" },
  { key: "done", icon: CheckCircle2, tone: "var(--mint)" },
  { key: "due_soon", icon: AlarmClock, tone: "var(--sun)" },
];

function FilterSelect<T extends string | number>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: T | undefined;
  onChange: (v: T | undefined) => void;
  options: { value: T; label: React.ReactNode }[];
}) {
  const tc = useTranslations("common");
  return (
    <div className="grid min-w-0 gap-1">
      <Label className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">
        {label}
      </Label>
      <Select
        value={value === undefined ? ALL : String(value)}
        onValueChange={(v) => {
          if (v === ALL) return onChange(undefined);
          const hit = options.find((o) => String(o.value) === v);
          onChange(hit?.value);
        }}
      >
        <SelectTrigger className={cn("h-9 w-full", value !== undefined && "border-primary/50 bg-primary/5")}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>{tc("all")}</SelectItem>
          {options.map((o) => (
            <SelectItem key={String(o.value)} value={String(o.value)}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

export default function TasksPage() {
  const t = useTranslations("tasks");
  const tt = useTranslations("taskTable");
  const tst = useTranslations("taskStatus");
  const tu = useTranslations("urgency");

  const [filters, setFilters] = useState<TaskFilters>({});
  const [dueSoon, setDueSoon] = useState(false);
  const set = <K extends keyof TaskFilters>(k: K, v: TaskFilters[K]) => setFilters((f) => ({ ...f, [k]: v }));

  const { data: tasks, isLoading } = useTasks(filters);
  const { data: stats } = useTaskStats();
  const { data: participants = [] } = useParticipants();
  const { data: directions = [] } = useDirections();
  const { data: meetings = [] } = useMeetings();
  const update = useUpdateTask();

  const rows = useMemo(
    () =>
      (tasks ?? [])
        .filter(
          (task) =>
            !dueSoon || (deadlineInfo(task.deadline, task.status).tone === "soon" && task.status !== "draft"),
        )
        .sort((a, b) => (a.deadline ?? "9999").localeCompare(b.deadline ?? "9999")),
    [tasks, dueSoon],
  );

  const pName = (id: number | null) => participants.find((p) => p.id === id)?.name;
  const dName = (id: number) => directions.find((d) => d.id === id)?.name ?? "—";
  const hasFilters = Object.values(filters).some((v) => v !== undefined && v !== false) || dueSoon;

  const onCounter = (key: CounterKey) => {
    if (key === "due_soon") {
      setDueSoon((v) => !v);
      set("status", undefined);
    } else {
      setDueSoon(false);
      set("status", filters.status === key ? undefined : key);
    }
  };

  return (
    <>
      <PageHeader
        eyebrow={t("subtitle")}
        title={t("title")}
        actions={
          <label className="bg-card shadow-soft inline-flex cursor-pointer items-center gap-2.5 rounded-xl border px-3 py-2 text-sm">
            <Switch checked={!!filters.mine} onCheckedChange={(v) => set("mine", v || undefined)} />
            {t("onlyMine")}
          </label>
        }
      />

      {/* Counters */}
      <div className="mb-6 grid grid-cols-2 gap-2.5 sm:mb-8 sm:gap-3 lg:grid-cols-4">
        {COUNTERS.map(({ key, icon: Icon, tone }) => {
          const active = key === "due_soon" ? dueSoon : filters.status === key;
          return (
            <button
              key={key}
              onClick={() => onCounter(key)}
              className={cn(
                "group bg-card shadow-soft relative overflow-hidden rounded-xl border p-3.5 text-left transition-all hover:-translate-y-px sm:p-5",
                active && "ring-2",
              )}
              style={{ ["--tw-ring-color" as string]: tone }}
            >
              <span className="absolute inset-x-0 top-0 h-[3px]" style={{ background: tone }} />
              <div className="text-muted-foreground flex items-center justify-between">
                <span className="text-sm">{t(`counters.${key}`)}</span>
                <Icon className="size-4" style={{ color: tone }} />
              </div>
              <div
                className="font-heading tabular mt-1 text-4xl font-bold tracking-tight sm:mt-3 sm:text-6xl"
                style={{ color: stats ? tone : undefined }}
              >
                {stats ? stats[key as keyof TaskStats] : "·"}
              </div>
            </button>
          );
        })}
      </div>

      {/* Filters */}
      <div className="bg-card shadow-soft mb-4 grid grid-cols-2 items-end gap-3 rounded-xl border p-3 sm:grid-cols-3 lg:grid-cols-[repeat(5,minmax(0,1fr))_auto]">
        <FilterSelect<TaskStatus>
          label={t("filters.status")}
          value={filters.status}
          onChange={(v) => {
            setDueSoon(false);
            set("status", v);
          }}
          options={TASK_STATUSES.map((s) => ({ value: s, label: tst(s) }))}
        />
        <FilterSelect<number>
          label={t("filters.assignee")}
          value={filters.assignee_id}
          onChange={(v) => set("assignee_id", v)}
          options={participants.map((p) => ({ value: p.id, label: p.name }))}
        />
        <FilterSelect<number>
          label={t("filters.direction")}
          value={filters.direction_id}
          onChange={(v) => set("direction_id", v)}
          options={directions.map((d) => ({ value: d.id, label: d.name }))}
        />
        <FilterSelect<Urgency>
          label={t("filters.urgency")}
          value={filters.urgency}
          onChange={(v) => set("urgency", v)}
          options={URGENCY_ORDER.map((u) => ({ value: u, label: tu(u) }))}
        />
        <FilterSelect<number>
          label={t("filters.meeting")}
          value={filters.meeting_id}
          onChange={(v) => set("meeting_id", v)}
          options={meetings.map((m) => ({ value: m.id, label: m.title }))}
        />
        <Button
          variant="ghost"
          className="h-9"
          disabled={!hasFilters}
          onClick={() => {
            setFilters({});
            setDueSoon(false);
          }}
        >
          <FilterX /> {t("filters.reset")}
        </Button>
      </div>

      {/* Table */}
      {isLoading ? (
        <Skeleton className="h-80 rounded-lg" />
      ) : rows.length === 0 ? (
        <EmptyState title={t("empty")} />
      ) : (
        <>
          {/* Mobile/tablet: cards */}
          <ul className="grid gap-3 sm:grid-cols-2 lg:hidden">
            {rows.map((task) => {
              const name = pName(task.assignee_participant_id);
              const tone = deadlineInfo(task.deadline, task.status).tone;
              return (
                <li
                  key={task.id}
                  className={cn(
                    "bg-card shadow-soft rounded-xl border p-4",
                    tone === "overdue" && "border-coral/40",
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="leading-snug font-medium">{task.text}</p>
                      <Link
                        href={`/meetings/${task.meeting_id}`}
                        className="text-muted-foreground hover:text-primary mt-0.5 block truncate text-xs"
                      >
                        № {task.meeting_id} · {task.meeting_title}
                      </Link>
                    </div>
                    <UrgencyMark urgency={task.urgency} withLabel={false} />
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
                    <span className="inline-flex min-w-0 items-center gap-2">
                      <ParticipantAvatar name={name ?? task.assignee_name} size="sm" />
                      <span className={cn("truncate text-sm", !name && "text-coral")}>
                        {name ?? task.assignee_name}
                      </span>
                    </span>
                    <DeadlineLabel deadline={task.deadline} status={task.status} />
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-2 border-t pt-3">
                    <span className="text-muted-foreground truncate text-xs">{dName(task.direction_id)}</span>
                    <StatusSelect
                      value={task.status}
                      disabled={update.isPending}
                      onChange={(status) =>
                        update.mutate({ id: task.id, status }, { onError: (e) => toast.error(e.message) })
                      }
                    />
                  </div>
                </li>
              );
            })}
          </ul>

          {/* Desktop: table */}
          <div className="bg-card shadow-soft hidden overflow-hidden rounded-xl border lg:block">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40">
                  <TableHead className="min-w-[18rem]">{tt("text")}</TableHead>
                  <TableHead>{tt("assignee")}</TableHead>
                  <TableHead>{tt("deadline")}</TableHead>
                  <TableHead>{tt("urgency")}</TableHead>
                  <TableHead>{tt("direction")}</TableHead>
                  <TableHead>{tt("status")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((task) => {
                  const name = pName(task.assignee_participant_id);
                  const tone = deadlineInfo(task.deadline, task.status).tone;
                  return (
                    <TableRow key={task.id} className={cn(tone === "overdue" && "bg-coral/[0.04]")}>
                      <TableCell className="whitespace-normal">
                        <div className="flex items-start gap-2">
                          <span className="font-medium">{task.text}</span>
                          {task.quote && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Quote className="text-primary mt-1 size-3 shrink-0" />
                              </TooltipTrigger>
                              <TooltipContent className="max-w-xs italic">«{task.quote}»</TooltipContent>
                            </Tooltip>
                          )}
                        </div>
                        <Link
                          href={`/meetings/${task.meeting_id}`}
                          className="text-muted-foreground hover:text-primary mt-0.5 block text-xs hover:underline"
                        >
                          № {task.meeting_id} · {task.meeting_title}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-2">
                          <ParticipantAvatar name={name ?? task.assignee_name} size="sm" />
                          <span className={cn("text-sm", !name && "text-coral")}>
                            {name ?? task.assignee_name}
                          </span>
                        </span>
                      </TableCell>
                      <TableCell>
                        <DeadlineLabel deadline={task.deadline} status={task.status} />
                      </TableCell>
                      <TableCell>
                        <UrgencyMark urgency={task.urgency} />
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {dName(task.direction_id)}
                      </TableCell>
                      <TableCell>
                        <StatusSelect
                          value={task.status}
                          disabled={update.isPending}
                          onChange={(status) =>
                            update.mutate({ id: task.id, status }, { onError: (e) => toast.error(e.message) })
                          }
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </>
  );
}
