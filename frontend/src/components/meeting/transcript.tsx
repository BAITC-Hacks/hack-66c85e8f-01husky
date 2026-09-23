"use client";

import { ClipboardCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useRef } from "react";
import type { Segment, Task } from "@/lib/api/types";
import { formatTimecode, speakerColor } from "@/lib/format";
import { cn } from "@/lib/utils";

export interface Focus {
  idx: number;
  quote?: string;
  /** bump to replay the highlight animation */
  nonce: number;
}

function Highlighted({ text, quote, nonce }: { text: string; quote?: string; nonce: number }) {
  if (!quote) return <>{text}</>;
  const at = text.toLowerCase().indexOf(quote.toLowerCase());
  if (at < 0)
    return (
      <mark key={nonce} className="marker-highlight rounded-sm bg-transparent text-inherit">
        {text}
      </mark>
    );
  return (
    <>
      {text.slice(0, at)}
      <mark key={nonce} className="marker-highlight rounded-sm bg-transparent px-0.5 text-inherit">
        {text.slice(at, at + quote.length)}
      </mark>
      {text.slice(at + quote.length)}
    </>
  );
}

export function Transcript({
  segments,
  tasks,
  nameOf,
  focus,
  onFocus,
  onTaskClick,
}: {
  segments: Segment[];
  tasks: Task[];
  nameOf: (speaker: string) => string | null;
  focus: Focus | null;
  onFocus: (f: Focus) => void;
  onTaskClick: (taskId: number) => void;
}) {
  const t = useTranslations("meeting");
  const tl = useTranslations("segmentLang");
  const refs = useRef<Map<number, HTMLLIElement>>(new Map());
  const tasksBySeg = useMemo(() => {
    const m = new Map<number, Task[]>();
    for (const task of tasks)
      if (task.segment_idx >= 0) m.set(task.segment_idx, [...(m.get(task.segment_idx) ?? []), task]);
    return m;
  }, [tasks]);

  useEffect(() => {
    if (!focus) return;
    // wait a frame: on mobile the transcript tab has just mounted and is still laying out
    const id = requestAnimationFrame(() =>
      refs.current.get(focus.idx)?.scrollIntoView({ behavior: "smooth", block: "center" }),
    );
    return () => cancelAnimationFrame(id);
  }, [focus]);

  if (!segments.length) {
    return <p className="text-muted-foreground px-6 py-16 text-center text-sm">{t("noTranscript")}</p>;
  }

  return (
    <ol className="divide-border/60 divide-y">
      {segments.map((s, i) => {
        const prev = segments[i - 1];
        const sameSpeaker = prev?.speaker === s.speaker;
        const active = focus?.idx === s.idx;
        const segTasks = tasksBySeg.get(s.idx);
        return (
          <li
            key={s.idx}
            ref={(el) => {
              if (el) refs.current.set(s.idx, el);
              else refs.current.delete(s.idx);
            }}
            className={cn(
              "group relative grid grid-cols-[2.75rem_1fr] gap-2 py-3 pr-4 pl-4 transition-colors sm:grid-cols-[3.25rem_1fr] sm:gap-3 sm:pr-6",
              active && "bg-brand-soft/70",
              sameSpeaker && "border-t-transparent pt-1",
            )}
          >
            <span
              className="absolute inset-y-0 left-0 w-[3px]"
              style={{ background: speakerColor(s.speaker) }}
            />
            <button
              onClick={() => onFocus({ idx: s.idx, nonce: Date.now() })}
              className="text-muted-foreground tabular hover:text-primary pt-0.5 text-left font-mono text-[11px]"
            >
              {formatTimecode(s.start)}
            </button>
            <div className="min-w-0 overflow-hidden">
              {!sameSpeaker && (
                <div className="mb-1 flex items-center gap-2">
                  <span className="text-sm font-semibold" style={{ color: speakerColor(s.speaker) }}>
                    {nameOf(s.speaker) ?? <span className="font-mono text-xs">{s.speaker}</span>}
                  </span>
                  {nameOf(s.speaker) && (
                    <span className="text-muted-foreground font-mono text-[10px]">{s.speaker}</span>
                  )}
                </div>
              )}
              <p className="leading-relaxed text-pretty">
                <Highlighted
                  text={s.text}
                  quote={active ? focus?.quote : undefined}
                  nonce={focus?.nonce ?? 0}
                />
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    "rounded border px-1 font-mono text-[9px] leading-4 tracking-wider",
                    s.lang === "kk" && "border-sun/50 text-sun",
                    s.lang === "mixed" && "border-mint/50 text-mint",
                    s.lang === "ru" && "text-muted-foreground",
                  )}
                >
                  {tl(s.lang)}
                </span>
                {segTasks?.map((task) => (
                  <button
                    key={task.id}
                    onClick={() => onTaskClick(task.id)}
                    className="bg-primary/10 text-primary hover:bg-primary/20 inline-flex max-w-full min-w-0 items-center gap-1 rounded-full px-2 py-px text-[11px] font-medium"
                  >
                    <ClipboardCheck className="size-3 shrink-0" />
                    <span className="truncate sm:max-w-[16rem]">{task.text}</span>
                  </button>
                ))}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
