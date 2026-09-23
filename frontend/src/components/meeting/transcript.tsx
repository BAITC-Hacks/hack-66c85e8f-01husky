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
  if (at < 0) return <mark key={nonce} className="marker-highlight rounded-sm bg-transparent text-inherit">{text}</mark>;
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
    for (const task of tasks) if (task.segment_idx >= 0) m.set(task.segment_idx, [...(m.get(task.segment_idx) ?? []), task]);
    return m;
  }, [tasks]);

  useEffect(() => {
    if (!focus) return;
    refs.current.get(focus.idx)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [focus]);

  if (!segments.length) {
    return <p className="px-6 py-16 text-center text-sm text-muted-foreground">{t("noTranscript")}</p>;
  }

  return (
    <ol className="divide-y divide-border/60">
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
              "group relative grid grid-cols-[3.25rem_1fr] gap-3 py-3 pr-4 pl-4 transition-colors sm:pr-6",
              active && "bg-gold-soft/40",
              sameSpeaker && "border-t-transparent pt-1",
            )}
          >
            <span className="absolute inset-y-0 left-0 w-[3px]" style={{ background: speakerColor(s.speaker) }} />
            <button
              onClick={() => onFocus({ idx: s.idx, nonce: Date.now() })}
              className="pt-0.5 text-left font-mono text-[11px] text-muted-foreground tabular hover:text-primary"
            >
              {formatTimecode(s.start)}
            </button>
            <div className="min-w-0">
              {!sameSpeaker && (
                <div className="mb-1 flex items-center gap-2">
                  <span className="text-sm font-semibold" style={{ color: speakerColor(s.speaker) }}>
                    {nameOf(s.speaker) ?? <span className="font-mono text-xs">{s.speaker}</span>}
                  </span>
                  {nameOf(s.speaker) && <span className="font-mono text-[10px] text-muted-foreground">{s.speaker}</span>}
                </div>
              )}
              <p className="leading-relaxed text-pretty">
                <Highlighted text={s.text} quote={active ? focus?.quote : undefined} nonce={focus?.nonce ?? 0} />
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    "rounded border px-1 font-mono text-[9px] leading-4 tracking-wider",
                    s.lang === "kk" && "border-gold/50 text-gold",
                    s.lang === "mixed" && "border-sage/50 text-sage",
                    s.lang === "ru" && "text-muted-foreground",
                  )}
                >
                  {tl(s.lang)}
                </span>
                {segTasks?.map((task) => (
                  <button
                    key={task.id}
                    onClick={() => onTaskClick(task.id)}
                    className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-px text-[11px] font-medium text-primary hover:bg-primary/20"
                  >
                    <ClipboardCheck className="size-3" />
                    <span className="max-w-[16rem] truncate">{task.text}</span>
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
