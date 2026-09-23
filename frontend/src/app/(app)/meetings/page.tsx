"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { EmptyState, PageHeader } from "@/components/common/bits";
import { MeetingRow } from "@/components/meetings/meeting-row";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMeetings } from "@/lib/api/queries/meetings";
import type { MeetingStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const FILTERS: (MeetingStatus | "all")[] = ["all", "draft", "processing", "confirmed", "failed"];

export default function MeetingsPage() {
  const t = useTranslations("meetings");
  const tc = useTranslations("common");
  const tst = useTranslations("meetingStatus");
  const [status, setStatus] = useState<MeetingStatus | "all">("all");
  const { data, isLoading } = useMeetings();

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: data?.length ?? 0 };
    for (const m of data ?? []) {
      const k = m.status === "uploaded" ? "processing" : m.status;
      c[k] = (c[k] ?? 0) + 1;
    }
    return c;
  }, [data]);

  const list = (data ?? []).filter(
    (m) => status === "all" || m.status === status || (status === "processing" && m.status === "uploaded"),
  );

  return (
    <>
      <PageHeader
        eyebrow={t("subtitle")}
        title={t("title")}
        actions={
          <Button asChild size="lg">
            <Link href="/meetings/new">
              <Plus data-icon="inline-start" />
              {t("new")}
            </Link>
          </Button>
        }
      />

      <div className="mb-6">
        <div className="sm:bg-card sm:shadow-soft flex flex-wrap gap-1.5 sm:inline-flex sm:gap-1 sm:rounded-full sm:border sm:p-1">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setStatus(f)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-medium whitespace-nowrap transition-colors",
                status === f
                  ? "bg-primary text-primary-foreground shadow-soft"
                  : "text-muted-foreground hover:text-foreground max-sm:bg-card max-sm:border",
              )}
            >
              {f === "all" ? tc("all") : tst(f)}
              <span className="font-mono text-[10px] opacity-70">{counts[f] ?? 0}</span>
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
      ) : list.length === 0 ? (
        <EmptyState
          title={t("empty")}
          hint={t("emptyHint")}
          action={
            <Button asChild>
              <Link href="/meetings/new">
                <Plus data-icon="inline-start" />
                {t("new")}
              </Link>
            </Button>
          }
        />
      ) : (
        <ul className="space-y-3">
          {list.map((m, i) => (
            <MeetingRow key={m.id} m={m} index={i} />
          ))}
        </ul>
      )}
    </>
  );
}
