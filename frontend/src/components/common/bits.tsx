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
          <div className="text-primary mb-2 text-xs font-semibold tracking-wide uppercase">{eyebrow}</div>
        )}
        <h1 className="font-heading text-3xl font-bold text-balance sm:text-4xl">{title}</h1>
        {subtitle && <p className="text-muted-foreground mt-1.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="border-border bg-card/60 flex flex-col items-center rounded-2xl border border-dashed px-6 py-16 text-center">
      <span className="bg-brand-soft text-primary mb-4 flex size-12 items-center justify-center rounded-2xl">
        <Sparkles className="size-5" />
      </span>
      <p className="font-heading text-lg font-medium">{title}</p>
      {hint && <p className="text-muted-foreground mt-1 max-w-md text-sm">{hint}</p>}
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
        "border-background text-primary-foreground inline-flex shrink-0 items-center justify-center rounded-full border font-medium",
        size === "sm" ? "size-6 text-[10px]" : "size-8 text-xs",
        className,
      )}
      style={{
        background: colorKey ? speakerColor(colorKey) : "linear-gradient(135deg, var(--brand), #e0509f)",
      }}
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
        <span className="border-background bg-muted inline-flex size-6 items-center justify-center rounded-full border text-[10px] font-medium">
          +{names.length - max}
        </span>
      )}
    </span>
  );
}

export function DeadlineLabel({
  deadline,
  status,
  raw,
}: {
  deadline: string | null;
  status: TaskStatus;
  raw?: string | null;
}) {
  const t = useTranslations("common");
  const tt = useTranslations("taskTable");
  const locale = useLocale();
  const { days, tone } = deadlineInfo(deadline, status);
  if (tone === "none") return <span className="text-muted-foreground text-sm">{tt("noDeadline")}</span>;
  const rel =
    days === 0
      ? t("today")
      : days === 1
        ? t("tomorrow")
        : days! < 0
          ? t("daysAgo", { count: -days! })
          : t("daysLeft", { count: days! });
  return (
    <span className="inline-flex flex-col leading-tight">
      <span
        className={cn(
          "tabular text-sm font-medium",
          tone === "overdue" && "text-coral",
          tone === "soon" && "text-sun",
          tone === "done" && "text-muted-foreground line-through",
        )}
      >
        {formatDate(deadline, locale, "d MMM")}
        <span className="ml-1.5 text-xs font-normal opacity-80">· {rel}</span>
      </span>
      {raw && <span className="text-muted-foreground text-[11px] italic">«{raw}»</span>}
    </span>
  );
}

/** Tiny horizontal meter for AI confidence, flagged below LOW_CONFIDENCE. */
export function ConfidenceMeter({ value, className }: { value: number; className?: string }) {
  const low = value < LOW_CONFIDENCE;
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)} title={`${Math.round(value * 100)}%`}>
      <span className="bg-muted relative h-1 w-10 overflow-hidden rounded-full">
        <span
          className={cn("absolute inset-y-0 left-0 rounded-full", low ? "bg-coral" : "bg-mint")}
          style={{ width: `${Math.round(value * 100)}%` }}
        />
      </span>
      <span className={cn("tabular font-mono text-[11px]", low ? "text-coral" : "text-muted-foreground")}>
        {Math.round(value * 100)}
      </span>
    </span>
  );
}

export function SpeakerChip({ label, name }: { label: string; name?: string | null }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="size-2.5 rounded-full" style={{ background: speakerColor(label) }} />
      <span className={cn("text-sm font-medium", !name && "text-muted-foreground font-mono text-xs")}>
        {name ?? label}
      </span>
    </span>
  );
}
