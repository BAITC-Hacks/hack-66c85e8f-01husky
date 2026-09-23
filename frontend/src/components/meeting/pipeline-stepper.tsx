"use client";

import { Check, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import type { Meeting } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const STAGES = ["upload", "stt", "diarize", "voiceprint", "extract", "summary"] as const;

/** Live view of the pipeline: progress_stage / progress_pct from polling (spec §7 Celery). */
export function PipelineStepper({ meeting }: { meeting: Meeting }) {
  const t = useTranslations("stages");
  const tm = useTranslations("meeting");
  const stage = meeting.progress_stage ?? "upload";
  const botRecording = stage === "bot_recording";
  const current = botRecording ? -1 : Math.max(0, STAGES.indexOf(stage as (typeof STAGES)[number]));
  const pct = Math.round((meeting.progress_pct ?? 0) * 100);

  return (
    <section className="overflow-hidden rounded-lg border bg-card">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b px-5 py-4 sm:px-6">
        <div>
          <h2 className="font-heading text-xl font-semibold">{botRecording ? t("bot_recording") : tm("processingTitle")}</h2>
          <p className="text-sm text-muted-foreground">{tm("processingHint")}</p>
        </div>
        <span className="font-mono text-4xl font-light text-primary tabular">{pct}%</span>
      </div>
      <div className="h-1 bg-primary/10">
        <div className="h-full bg-primary transition-[width] duration-1000 ease-out" style={{ width: `${Math.max(2, pct)}%` }} />
      </div>
      <ol className="grid grid-cols-2 gap-px bg-border sm:grid-cols-3 lg:grid-cols-6">
        {STAGES.map((s, i) => {
          const done = i < current;
          const active = i === current;
          return (
            <li key={s} className={cn("flex items-center gap-3 bg-card px-4 py-3.5", active && "bg-gold-soft/40")}>
              <span
                className={cn(
                  "flex size-7 shrink-0 items-center justify-center rounded-full border font-mono text-[11px]",
                  done && "border-sage bg-sage text-white",
                  active && "border-primary text-primary",
                  !done && !active && "text-muted-foreground",
                )}
              >
                {done ? <Check className="size-3.5" /> : active ? <Loader2 className="size-3.5 animate-spin" /> : i + 1}
              </span>
              <span className={cn("text-sm", active ? "font-medium" : "text-muted-foreground", done && "text-foreground")}>
                {t(s)}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
