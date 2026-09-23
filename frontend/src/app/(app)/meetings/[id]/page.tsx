"use client";

import { AlertOctagon, ArrowLeft, CalendarDays, Clock, RefreshCcw, UsersRound } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useMemo, useState } from "react";
import { PrivacyBadge } from "@/components/brand/privacy-badge";
import { SealStamp } from "@/components/brand/seal-stamp";
import { MeetingStatusBadge } from "@/components/common/badges";
import { EmptyState } from "@/components/common/bits";
import { ActionsBar } from "@/components/meeting/actions-bar";
import { LangMix } from "@/components/meeting/lang-mix";
import { PipelineStepper } from "@/components/meeting/pipeline-stepper";
import { SpeakerRibbon } from "@/components/meeting/speaker-ribbon";
import { SpeakersPanel } from "@/components/meeting/speakers-panel";
import { SummaryPanel } from "@/components/meeting/summary-panel";
import { TasksPanel } from "@/components/meeting/tasks-panel";
import { Transcript, type Focus } from "@/components/meeting/transcript";
import { SourceIcon } from "@/components/meetings/source-icon";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useDirections } from "@/lib/api/queries/directions";
import { useMeeting, useMeetingAction } from "@/lib/api/queries/meetings";
import { useParticipants } from "@/lib/api/queries/participants";
import type { Task } from "@/lib/api/types";
import { formatDate, formatDuration } from "@/lib/format";

export default function MeetingPage() {
  const { id } = useParams<{ id: string }>();
  const meetingId = Number(id);
  const t = useTranslations("meeting");
  const tb = useTranslations("brand");
  const ts = useTranslations("source");
  const tp = useTranslations("platform");
  const locale = useLocale();

  const { data, isLoading, error } = useMeeting(meetingId);
  const { data: allParticipants = [] } = useParticipants();
  const { data: directions = [] } = useDirections();
  const reprocess = useMeetingAction(meetingId, "reprocess");

  const [tab, setTab] = useState("tasks");
  const [focus, setFocus] = useState<Focus | null>(null);
  const [highlightTask, setHighlightTask] = useState<number | null>(null);
  const [justConfirmed, setJustConfirmed] = useState(false);

  const nameOf = useCallback(
    (speaker: string) => {
      const pid = data?.speaker_map.find((r) => r.speaker === speaker)?.participant_id;
      return allParticipants.find((p) => p.id === pid)?.name ?? null;
    },
    [data?.speaker_map, allParticipants],
  );

  const onQuote = (task: Task) => {
    if (task.segment_idx < 0) return;
    setFocus({ idx: task.segment_idx, quote: task.quote, nonce: Date.now() });
  };
  const onTaskClick = (taskId: number) => {
    setTab("tasks");
    setHighlightTask(taskId);
    requestAnimationFrame(() =>
      document.getElementById(`task-${taskId}`)?.scrollIntoView({ behavior: "smooth", block: "center" }),
    );
    setTimeout(() => setHighlightTask((cur) => (cur === taskId ? null : cur)), 2000);
  };

  const unresolved = useMemo(
    () => data?.speaker_map.filter((r) => !r.participant_id).length ?? 0,
    [data?.speaker_map],
  );

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-24" />
        <Skeleton className="h-96" />
      </div>
    );
  }
  if (error || !data) {
    return <EmptyState title={error?.message ?? "404"} action={<Button asChild variant="outline"><Link href="/meetings">{t("back")}</Link></Button>} />;
  }

  const m = data.meeting;
  const busy = m.status === "processing" || m.status === "uploaded";
  const isDraft = m.status === "draft";
  const hasContent = !busy && m.status !== "failed";
  const pickerParticipants = [
    ...data.participants,
    ...allParticipants.filter((p) => !data.participants.some((x) => x.id === p.id)),
  ];

  return (
    <div className="grid gap-6">
      {/* ---------- Header ---------- */}
      <header className="relative border-b pb-6">
        <Link
          href="/meetings"
          className="mb-3 inline-flex items-center gap-1 font-mono text-[11px] tracking-[0.18em] text-muted-foreground uppercase hover:text-foreground"
        >
          <ArrowLeft className="size-3" /> {t("back")} · № {m.id}
        </Link>
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0 lg:pr-40">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <MeetingStatusBadge status={m.status} />
              {m.model_info && <PrivacyBadge modelInfo={m.model_info} />}
            </div>
            <h1 className="font-heading text-3xl font-semibold text-balance sm:text-4xl">{m.title}</h1>
            <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground">
              <div className="inline-flex items-center gap-1.5">
                <CalendarDays className="size-4" />
                <dt className="sr-only">{t("date")}</dt>
                <dd>{formatDate(m.meeting_date, locale, "d MMMM yyyy")}</dd>
              </div>
              <div className="inline-flex items-center gap-1.5">
                <Clock className="size-4" />
                <dt className="sr-only">{t("duration")}</dt>
                <dd>{formatDuration(m.duration_sec)}</dd>
              </div>
              <div className="inline-flex items-center gap-1.5">
                <SourceIcon source={m.source} className="size-4" />
                <dt className="sr-only">{t("source")}</dt>
                <dd>{m.platform ? tp(m.platform) : ts(m.source)}</dd>
              </div>
              <div className="inline-flex items-center gap-1.5">
                <UsersRound className="size-4" />
                <dd>{data.participants.length}</dd>
              </div>
            </dl>
            {m.language_stats && (
              <div className="mt-4 max-w-sm">
                <LangMix stats={m.language_stats} />
              </div>
            )}
          </div>
          <ActionsBar meeting={m} onConfirmed={() => setJustConfirmed(true)} />
        </div>
        {m.status === "confirmed" && (
          <SealStamp
            key={justConfirmed ? "fresh" : "static"}
            label={tb("seal")}
            date={formatDate(m.confirmed_at ?? m.meeting_date, locale, "dd.MM.yyyy")}
            refNo={m.sed_ref}
            animate={justConfirmed}
            className="absolute top-0 right-0 hidden size-36 lg:block"
          />
        )}
      </header>

      {/* ---------- Processing / failure ---------- */}
      {busy && <PipelineStepper meeting={m} />}
      {m.status === "failed" && (
        <section className="flex flex-col gap-4 rounded-lg border border-brick/40 bg-brick/5 p-6 sm:flex-row sm:items-center">
          <AlertOctagon className="size-8 shrink-0 text-brick" />
          <div className="flex-1">
            <p className="font-heading text-lg font-semibold">{t("failed")}</p>
            <p className="font-mono text-sm text-muted-foreground">{m.error}</p>
          </div>
          {m.has_audio && (
            <Button variant="outline" onClick={() => reprocess.mutate()} disabled={reprocess.isPending}>
              <RefreshCcw /> {t("actions.reprocess")}
            </Button>
          )}
        </section>
      )}

      {/* ---------- Protocol workspace ---------- */}
      {hasContent && (
        <>
          {data.segments.length > 0 && (
            <SpeakerRibbon
              segments={data.segments}
              duration={m.duration_sec ?? 0}
              nameOf={nameOf}
              activeIdx={focus?.idx ?? null}
              onSelect={(idx) => setFocus({ idx, nonce: Date.now() })}
            />
          )}

          <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
            <section className="overflow-hidden rounded-lg border bg-card lg:sticky lg:top-20">
              <div className="flex items-baseline justify-between border-b px-4 py-3 sm:px-6">
                <h2 className="font-heading text-lg font-semibold">{t("transcript")}</h2>
                <span className="font-mono text-[11px] text-muted-foreground">
                  {t("segments", { count: data.segments.length })}
                </span>
              </div>
              <div className="max-h-[70vh] overflow-y-auto lg:max-h-[calc(100svh-9rem)]">
                <Transcript
                  segments={data.segments}
                  tasks={data.tasks}
                  nameOf={nameOf}
                  focus={focus}
                  onFocus={setFocus}
                  onTaskClick={onTaskClick}
                />
              </div>
            </section>

            <Tabs value={tab} onValueChange={setTab} className="gap-4">
              <TabsList className="grid h-10 w-full grid-cols-3">
                <TabsTrigger value="tasks" className="gap-1.5">
                  {t("tasks")}
                  <span className="font-mono text-[10px] opacity-60">{data.tasks.length}</span>
                </TabsTrigger>
                <TabsTrigger value="speakers" className="gap-1.5">
                  {t("speakers")}
                  {unresolved > 0 && <span className="size-1.5 rounded-full bg-brick" />}
                </TabsTrigger>
                <TabsTrigger value="summary">{t("summary")}</TabsTrigger>
              </TabsList>
              <TabsContent value="tasks">
                <TasksPanel
                  meetingId={m.id}
                  tasks={data.tasks}
                  participants={pickerParticipants}
                  directions={directions}
                  readOnly={!isDraft}
                  highlightedId={highlightTask}
                  onQuote={onQuote}
                />
              </TabsContent>
              <TabsContent value="speakers">
                <SpeakersPanel
                  meetingId={m.id}
                  speakerMap={data.speaker_map}
                  segments={data.segments}
                  meetingParticipants={data.participants}
                  allParticipants={allParticipants}
                  readOnly={!isDraft}
                />
              </TabsContent>
              <TabsContent value="summary">
                <SummaryPanel key={data.summary ?? ""} meetingId={m.id} summary={data.summary} editable={isDraft} />
              </TabsContent>
            </Tabs>
          </div>
        </>
      )}
    </div>
  );
}
