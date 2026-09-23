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
        className="group relative grid grid-cols-[3.5rem_1fr_auto] items-center gap-4 overflow-hidden rounded-xl border bg-card shadow-soft px-4 py-4 transition-all hover:-translate-y-px hover:border-primary/40 hover:shadow-lift sm:grid-cols-[4.5rem_1fr_auto_auto] sm:px-5"
      >
        {/* date block, like a register column */}
        <div className="flex flex-col items-center border-r pr-4 text-center">
          <span className="font-heading text-3xl leading-none font-bold text-primary tabular">{formatDate(m.meeting_date, locale, "dd")}</span>
          <span className="mt-1 font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
            {formatDate(m.meeting_date, locale, "MMM yy")}
          </span>
        </div>

        <div className="min-w-0">
          <div className="mb-1 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-muted-foreground">
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
          <h3 className="truncate font-heading text-lg font-medium group-hover:text-primary">{m.title}</h3>
          <div className="mt-2 flex items-center gap-3 sm:hidden">
            <MeetingStatusBadge status={m.status} />
            <span className="text-xs text-muted-foreground">{t("tasksCount", { count: m.tasks_count })}</span>
          </div>
        </div>

        <div className="hidden flex-col items-end gap-2 sm:flex">
          <MeetingStatusBadge status={m.status} />
          <div className="flex items-center gap-3">
            <span className={cn("text-xs text-muted-foreground", m.tasks_count && "text-foreground")}>
              {t("tasksCount", { count: m.tasks_count })}
            </span>
            <AvatarStack names={m.participants.map((p) => p.name)} />
          </div>
        </div>

        <ChevronRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />

        {busy && (
          <span className="absolute inset-x-0 bottom-0 h-[2px] bg-primary/15">
            <span
              className="block h-full bg-primary transition-[width] duration-700"
              style={{ width: `${Math.max(4, Math.round((m.progress_pct ?? 0) * 100))}%` }}
            />
          </span>
        )}
      </Link>
    </li>
  );
}
