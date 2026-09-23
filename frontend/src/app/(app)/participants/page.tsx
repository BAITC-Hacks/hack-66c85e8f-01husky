"use client";

import { AudioWaveform, ChevronRight, Search, UserPlus } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { EmptyState, PageHeader, ParticipantAvatar } from "@/components/common/bits";
import { GuestDialog } from "@/components/participants/guest-dialog";
import { VoiceprintSheet } from "@/components/participants/voiceprint-sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useParticipants } from "@/lib/api/queries/participants";
import { cn } from "@/lib/utils";

export default function ParticipantsPage() {
  const t = useTranslations("participants");
  const tc = useTranslations("common");
  const { data = [], isLoading } = useParticipants();
  const [q, setQ] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const selected = data.find((p) => p.id === openId) ?? null;

  const list = data.filter((p) =>
    `${p.name} ${p.email ?? ""} ${p.position ?? ""}`.toLowerCase().includes(q.trim().toLowerCase()),
  );
  const withPrint = data.filter((p) => p.has_voiceprint).length;

  return (
    <>
      <PageHeader
        eyebrow={t("subtitle")}
        title={t("title")}
        subtitle={
          <span className="inline-flex items-center gap-1.5">
            <AudioWaveform className="text-mint size-4" />
            {withPrint} / {data.length} · {t("hasVoiceprint")}
          </span>
        }
        actions={
          <GuestDialog
            title={t("add")}
            trigger={
              <Button size="lg">
                <UserPlus /> {t("add")}
              </Button>
            }
          />
        }
      />

      <div className="relative mb-4 max-w-sm">
        <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={tc("search")}
          className="h-10 pl-9"
        />
      </div>

      {isLoading ? (
        <Skeleton className="h-72 rounded-lg" />
      ) : list.length === 0 ? (
        <EmptyState title={t("empty")} />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {list.map((p) => (
            <li key={p.id}>
              <button
                onClick={() => setOpenId(p.id)}
                className="group bg-card shadow-soft hover:border-primary/40 flex w-full items-center gap-3 rounded-xl border p-4 text-left transition-all hover:-translate-y-px"
              >
                <ParticipantAvatar name={p.name} className="size-11 text-sm" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{p.name}</span>
                  <span className="text-muted-foreground block truncate text-sm">
                    {p.position ?? p.email ?? "—"}
                  </span>
                  <span className="mt-1.5 flex flex-wrap gap-1.5">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full border px-1.5 py-px text-[11px]",
                        p.has_voiceprint
                          ? "border-mint/40 bg-mint/10 text-mint"
                          : "text-muted-foreground border-dashed",
                      )}
                    >
                      <AudioWaveform className="size-3" />
                      {p.has_voiceprint ? t("hasVoiceprint") : t("noVoiceprint")}
                    </span>
                    <span className="text-muted-foreground rounded-full border px-1.5 py-px font-mono text-[10px] uppercase">
                      {p.user_id ? t("account") : t("guest")}
                    </span>
                  </span>
                </span>
                <ChevronRight className="text-muted-foreground size-4 transition-transform group-hover:translate-x-0.5" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <VoiceprintSheet participant={selected} onOpenChange={(o) => !o && setOpenId(null)} />
    </>
  );
}
