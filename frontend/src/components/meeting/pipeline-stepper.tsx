"use client";

import { Check, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import type { Meeting } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const STAGES = ["upload", "stt", "diarize", "voiceprint", "extract", "summary"] as const;

/** Backend progress_stage values that don't have a step of their own. */
const STAGE_ALIASES: Record<string, (typeof STAGES)[number]> = {
  queued: "upload",
  loading_model: "upload",
  privacy: "summary",
  done: "summary",
};
/** Stages before any audio exists: the meeting is waiting for the bot or the live recording. */
const WAITING = new Set(["bot_joining", "recording"]);

/** Live view of the pipeline: progress_stage / progress_pct from polling (spec §7 Celery). */
export function PipelineStepper({ meeting }: { meeting: Meeting }) {
  const t = useTranslations("stages");
  const tm = useTranslations("meeting");
  const raw = meeting.progress_stage ?? "upload";
  const waiting = WAITING.has(raw);
  const stage = STAGE_ALIASES[raw] ?? raw;
  const current = waiting ? -1 : Math.max(0, STAGES.indexOf(stage as (typeof STAGES)[number]));
  const pct = Math.round(meeting.progress_pct);

  return (
    <section className="bg-card shadow-soft overflow-hidden rounded-xl border">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b px-5 py-4 sm:px-6">
        <div>
          <h2 className="font-heading text-xl font-semibold">
            {waiting ? t(raw as "bot_joining" | "recording") : tm("processingTitle")}
          </h2>
          <p className="text-muted-foreground text-sm">{tm("processingHint")}</p>
        </div>
        <span className="text-primary tabular font-mono text-4xl font-light">{pct}%</span>
      </div>
      <div className="bg-primary/10 h-1">
        <div
          className="bg-primary h-full transition-[width] duration-1000 ease-out"
          style={{ width: `${Math.max(2, pct)}%` }}
        />
      </div>
      <ol className="bg-border grid grid-cols-2 gap-px sm:grid-cols-3 lg:grid-cols-6">
        {STAGES.map((s, i) => {
          const done = i < current;
          const active = i === current;
          return (
            <li
              key={s}
              className={cn("bg-card flex items-center gap-3 px-4 py-3.5", active && "bg-brand-soft/70")}
            >
              <span
                className={cn(
                  "flex size-7 shrink-0 items-center justify-center rounded-full border font-mono text-[11px]",
                  done && "border-mint bg-mint text-white",
                  active && "border-primary text-primary",
                  !done && !active && "text-muted-foreground",
                )}
              >
                {done ? (
                  <Check className="size-3.5" />
                ) : active ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  i + 1
                )}
              </span>
              <span
                className={cn(
                  "text-sm",
                  active ? "font-medium" : "text-muted-foreground",
                  done && "text-foreground",
                )}
              >
                {t(s)}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
