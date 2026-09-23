"use client";

import { ChevronRight, Clock } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { AvatarStack } from "@/components/common/bits";
import { MeetingStatusBadge } from "@/components/common/badges";
import type { MeetingListItem } from "@/lib/api/types";
import { formatDate, formatDuration } from "@/lib/format";
import { cn } from "@/lib/utils";
import { SourceIcon } from "./source-icon";

export function MeetingRow({ m, index }: { m: MeetingListItem; index: number }) {
  const t = useTranslations("meetings");
  const ts = useTranslations("source");
  const tp = useTranslations("platform");
  const locale = useLocale();
  const busy = m.status === "processing" || m.status === "uploaded";

  return (
    <li className="animate-rise" style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}>
      <Link
        href={`/meetings/${m.id}`}
        className="group bg-card shadow-soft hover:border-primary/40 hover:shadow-lift relative grid grid-cols-[3.25rem_1fr_auto] items-center gap-3 overflow-hidden rounded-xl border px-4 py-4 transition-all hover:-translate-y-px sm:grid-cols-[4.5rem_1fr_auto_auto] sm:gap-4 sm:px-5"
      >
        {/* date block, like a register column */}
        <div className="flex flex-col items-center border-r pr-3 text-center sm:pr-4">
          <span className="font-heading text-primary tabular text-3xl leading-none font-bold">
            {formatDate(m.meeting_date, locale, "dd")}
          </span>
          <span className="text-muted-foreground mt-1 font-mono text-[9px] tracking-wide whitespace-nowrap uppercase sm:text-[10px]">
            {formatDate(m.meeting_date, locale, "MMM")}
          </span>
        </div>

        <div className="min-w-0">
          <div className="text-muted-foreground mb-1 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px]">
            <span>{t("registerNo", { id: m.id })}</span>
            <span className="inline-flex items-center gap-1">
              <SourceIcon source={m.source} className="size-3" />
              {m.platform ? tp(m.platform) : ts(m.source)}
            </span>
            <span className="inline-flex items-center gap-1">
              <Clock className="size-3" />
              {formatDuration(m.duration_sec)}
            </span>
            <span className="uppercase">{m.output_language === "kk" ? "KZ" : "RU"}</span>
          </div>
          <h3 className="font-heading group-hover:text-primary line-clamp-2 text-base leading-snug font-semibold sm:truncate sm:text-lg">
            {m.title}
          </h3>
          <div className="mt-2 flex items-center gap-3 sm:hidden">
            <MeetingStatusBadge status={m.status} />
            <span className="text-muted-foreground text-xs">{t("tasksCount", { count: m.tasks_count })}</span>
          </div>
        </div>

        <div className="hidden flex-col items-end gap-2 sm:flex">
          <MeetingStatusBadge status={m.status} />
          <div className="flex items-center gap-3">
            <span className={cn("text-muted-foreground text-xs", m.tasks_count && "text-foreground")}>
              {t("tasksCount", { count: m.tasks_count })}
            </span>
            <AvatarStack names={m.participants.map((p) => p.name)} />
          </div>
        </div>

        <ChevronRight className="text-muted-foreground size-4 transition-transform group-hover:translate-x-0.5" />

        {busy && (
          <span className="bg-primary/15 absolute inset-x-0 bottom-0 h-[2px]">
            <span
              className="bg-primary block h-full transition-[width] duration-700"
              style={{ width: `${Math.max(4, Math.round((m.progress_pct ?? 0) * 100))}%` }}
            />
          </span>
        )}
      </Link>
    </li>
  );
}
