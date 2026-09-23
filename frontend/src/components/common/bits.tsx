"use client";

import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { Sparkles } from "lucide-react";
import type { TaskStatus } from "@/lib/api/types";
import { deadlineInfo, formatDate, initials, LOW_CONFIDENCE, speakerColor } from "@/lib/format";
import { cn } from "@/lib/utils";

export function PageHeader({
  title,
  subtitle,
  actions,
  eyebrow,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  eyebrow?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-col gap-4 pb-2 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {eyebrow && (
          <div className="mb-2 text-xs font-semibold tracking-wide text-primary uppercase">{eyebrow}</div>
        )}
        <h1 className="font-heading text-3xl font-bold text-balance sm:text-4xl">{title}</h1>
        {subtitle && <p className="mt-1.5 text-muted-foreground">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-border bg-card/60 px-6 py-16 text-center">
      <span className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-brand-soft text-primary">
        <Sparkles className="size-5" />
      </span>
      <p className="font-heading text-lg font-medium">{title}</p>
      {hint && <p className="mt-1 max-w-md text-sm text-muted-foreground">{hint}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ParticipantAvatar({
  name,
  size = "md",
  className,
  colorKey,
}: {
  name: string;
  size?: "sm" | "md";
  className?: string;
  colorKey?: string;
}) {
  return (
    <span
      title={name}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full border border-background font-medium text-primary-foreground",
        size === "sm" ? "size-6 text-[10px]" : "size-8 text-xs",
        className,
      )}
      style={{ background: colorKey ? speakerColor(colorKey) : "linear-gradient(135deg, var(--brand), #e0509f)" }}
    >
      {initials(name)}
    </span>
  );
}

export function AvatarStack({ names, max = 4 }: { names: string[]; max?: number }) {
  const shown = names.slice(0, max);
  return (
    <span className="flex -space-x-1.5">
      {shown.map((n, i) => (
        <ParticipantAvatar key={n + i} name={n} size="sm" colorKey={`S${i}`} />
      ))}
      {names.length > max && (
        <span className="inline-flex size-6 items-center justify-center rounded-full border border-background bg-muted text-[10px] font-medium">
          +{names.length - max}
        </span>
      )}
    </span>
  );
}

export function DeadlineLabel({ deadline, status, raw }: { deadline: string | null; status: TaskStatus; raw?: string | null }) {
  const t = useTranslations("common");
  const tt = useTranslations("taskTable");
  const locale = useLocale();
  const { days, tone } = deadlineInfo(deadline, status);
  if (tone === "none") return <span className="text-sm text-muted-foreground">{tt("noDeadline")}</span>;
  const rel =
    days === 0 ? t("today") : days === 1 ? t("tomorrow") : days! < 0 ? t("daysAgo", { count: -days! }) : t("daysLeft", { count: days! });
  return (
    <span className="inline-flex flex-col leading-tight">
      <span
        className={cn(
          "text-sm font-medium tabular",
          tone === "overdue" && "text-coral",
          tone === "soon" && "text-sun",
          tone === "done" && "text-muted-foreground line-through",
        )}
      >
        {formatDate(deadline, locale, "d MMM")}
        <span className="ml-1.5 text-xs font-normal opacity-80">· {rel}</span>
      </span>
      {raw && <span className="text-[11px] text-muted-foreground italic">«{raw}»</span>}
    </span>
  );
}

/** Tiny horizontal meter for AI confidence, flagged below LOW_CONFIDENCE. */
export function ConfidenceMeter({ value, className }: { value: number; className?: string }) {
  const low = value < LOW_CONFIDENCE;
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)} title={`${Math.round(value * 100)}%`}>
      <span className="relative h-1 w-10 overflow-hidden rounded-full bg-muted">
        <span
          className={cn("absolute inset-y-0 left-0 rounded-full", low ? "bg-coral" : "bg-mint")}
          style={{ width: `${Math.round(value * 100)}%` }}
        />
      </span>
      <span className={cn("font-mono text-[11px] tabular", low ? "text-coral" : "text-muted-foreground")}>
        {Math.round(value * 100)}
      </span>
    </span>
  );
}

export function SpeakerChip({ label, name }: { label: string; name?: string | null }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="size-2.5 rounded-full" style={{ background: speakerColor(label) }} />
      <span className={cn("text-sm font-medium", !name && "font-mono text-xs text-muted-foreground")}>{name ?? label}</span>
    </span>
  );
}
