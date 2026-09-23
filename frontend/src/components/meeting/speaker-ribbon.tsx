"use client";

import { useTranslations } from "next-intl";
import { useMemo } from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Segment } from "@/lib/api/types";
import { formatTimecode, speakerColor } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Diarization timeline: one lane per speaker across the whole meeting.
 * Click a block → jump to that segment in the transcript.
 */
export function SpeakerRibbon({
  segments,
  duration,
  nameOf,
  activeIdx,
  onSelect,
}: {
  segments: Segment[];
  duration: number;
  nameOf: (speaker: string) => string | null;
  activeIdx: number | null;
  onSelect: (idx: number) => void;
}) {
  const t = useTranslations("meeting");
  const speakers = useMemo(() => [...new Set(segments.map((s) => s.speaker))].sort(), [segments]);
  const total = Math.max(duration, segments.at(-1)?.end ?? 0, 1);
  const share = useMemo(() => {
    const m: Record<string, number> = {};
    for (const s of segments) m[s.speaker] = (m[s.speaker] ?? 0) + (s.end - s.start);
    return m;
  }, [segments]);
  const ticks = [0, 0.25, 0.5, 0.75, 1];

  return (
    <section className="rounded-xl border bg-card shadow-soft p-4 sm:p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <h3 className="text-xs font-semibold tracking-wide text-primary uppercase">{t("timeline")}</h3>
        <span className="font-mono text-[11px] text-muted-foreground">{formatTimecode(total)}</span>
      </div>
      <div className="grid gap-1.5">
        {speakers.map((sp) => (
          <div key={sp} className="grid grid-cols-[7rem_1fr_2.5rem] items-center gap-3 sm:grid-cols-[10rem_1fr_3rem]">
            <span className="flex min-w-0 items-center gap-1.5 text-xs">
              <span className="size-2 shrink-0 rounded-full" style={{ background: speakerColor(sp) }} />
              <span className={cn("truncate", !nameOf(sp) && "font-mono text-muted-foreground")}>{nameOf(sp) ?? sp}</span>
            </span>
            <div className="relative h-5 rounded-sm bg-muted/60">
              {segments
                .filter((s) => s.speaker === sp)
                .map((s) => (
                  <Tooltip key={s.idx}>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => onSelect(s.idx)}
                        className={cn(
                          "absolute inset-y-0.5 rounded-[2px] transition-all hover:inset-y-0 hover:brightness-110",
                          activeIdx === s.idx && "inset-y-0 ring-2 ring-foreground/70",
                        )}
                        style={{
                          left: `${(s.start / total) * 100}%`,
                          width: `max(3px, ${((s.end - s.start) / total) * 100}%)`,
                          background: speakerColor(sp),
                        }}
                        aria-label={`${formatTimecode(s.start)} ${nameOf(sp) ?? sp}`}
                      />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <span className="font-mono text-[10px] opacity-70">{formatTimecode(s.start)}</span>
                      <p className="line-clamp-3">{s.text}</p>
                    </TooltipContent>
                  </Tooltip>
                ))}
            </div>
            <span className="text-right font-mono text-[11px] text-muted-foreground tabular">
              {Math.round(((share[sp] ?? 0) / total) * 100)}%
            </span>
          </div>
        ))}
      </div>
      <div className="mt-1.5 grid grid-cols-[7rem_1fr_2.5rem] gap-3 sm:grid-cols-[10rem_1fr_3rem]">
        <span />
        <div className="relative h-3">
          {ticks.map((f, i) => (
            <span
              key={f}
              className={cn(
                "absolute -translate-x-1/2 font-mono text-[9px] text-muted-foreground first:translate-x-0 last:-translate-x-full",
                i % 2 === 1 && "hidden sm:inline",
              )}
              style={{ left: `${f * 100}%` }}
            >
              {formatTimecode(total * f)}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
