"use client";

import { AudioWaveform, Bot, Hand, HelpCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ConfidenceMeter } from "@/components/common/bits";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAssignSpeakers } from "@/lib/api/queries/meetings";
import type { Participant, Segment, SpeakerMapping, SpeakerSource } from "@/lib/api/types";
import { formatTimecode, speakerColor } from "@/lib/format";
import { cn } from "@/lib/utils";

const SOURCE_ICON: Record<SpeakerSource, typeof Bot> = {
  voiceprint: AudioWaveform,
  llm: Bot,
  manual: Hand,
  none: HelpCircle,
};
const SOURCE_TONE: Record<SpeakerSource, string> = {
  voiceprint: "text-mint bg-mint/10 border-mint/30",
  llm: "text-primary bg-primary/10 border-primary/30",
  manual: "text-foreground bg-muted border-border",
  none: "text-coral bg-coral/10 border-coral/30",
};

const NONE = "__none";

export function SpeakersPanel({
  meetingId,
  speakerMap,
  segments,
  meetingParticipants,
  allParticipants,
  readOnly,
}: {
  meetingId: number;
  speakerMap: SpeakerMapping[];
  segments: Segment[];
  meetingParticipants: Participant[];
  allParticipants: Participant[];
  readOnly: boolean;
}) {
  const t = useTranslations("meeting");
  const ts = useTranslations("speakerSource");
  const assign = useAssignSpeakers(meetingId);
  const others = allParticipants.filter((p) => !meetingParticipants.some((m) => m.id === p.id));

  const rows = [...speakerMap];
  for (const sp of new Set(segments.map((s) => s.speaker))) {
    if (!rows.some((r) => r.speaker === sp))
      rows.push({ speaker: sp, participant_id: null, source: "none", confidence: 0 });
  }
  rows.sort((a, b) => a.speaker.localeCompare(b.speaker));

  const stats = (sp: string) => {
    const segs = segments.filter((s) => s.speaker === sp);
    return { count: segs.length, time: segs.reduce((a, s) => a + s.end - s.start, 0), first: segs[0]?.text };
  };

  return (
    <ul className="grid gap-3">
      {rows.map((r) => {
        const Icon = SOURCE_ICON[r.source];
        const st = stats(r.speaker);
        return (
          <li
            key={r.speaker}
            className={cn(
              "bg-card shadow-soft rounded-xl border p-4",
              r.source === "none" && "border-coral/40 border-dashed",
            )}
          >
            <div className="flex items-center gap-3">
              <span
                className="flex size-9 shrink-0 items-center justify-center rounded-full font-mono text-[11px] font-semibold text-white"
                style={{ background: speakerColor(r.speaker) }}
              >
                {r.speaker.replace(/\D+/g, "")}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-muted-foreground font-mono text-xs">{r.speaker}</div>
                <div className="text-muted-foreground text-xs">
                  {t("segments", { count: st.count })} · {formatTimecode(st.time)}
                </div>
              </div>
              <span
                className={cn(
                  "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
                  SOURCE_TONE[r.source],
                )}
              >
                <Icon className="size-3" />
                {ts(r.source)}
              </span>
            </div>
            {st.first && (
              <p className="text-muted-foreground mt-2 line-clamp-1 text-xs italic">«{st.first}»</p>
            )}
            <div className="mt-3 flex items-center gap-3">
              <Select
                disabled={readOnly || assign.isPending}
                value={r.participant_id ? String(r.participant_id) : NONE}
                onValueChange={(v) =>
                  assign.mutate([{ speaker: r.speaker, participant_id: v === NONE ? null : Number(v) }], {
                    onSuccess: () => toast.success(t("speakerSaved")),
                  })
                }
              >
                <SelectTrigger className="h-9 flex-1">
                  <SelectValue placeholder={t("selectParticipant")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NONE}>
                    <span className="text-muted-foreground">{t("unassigned")}</span>
                  </SelectItem>
                  <SelectSeparator />
                  <SelectGroup>
                    {meetingParticipants.map((p) => (
                      <SelectItem key={p.id} value={String(p.id)}>
                        {p.name}
                        {p.has_voiceprint && <AudioWaveform className="text-mint size-3" />}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                  {others.length > 0 && (
                    <>
                      <SelectSeparator />
                      <SelectGroup>
                        <SelectLabel>…</SelectLabel>
                        {others.map((p) => (
                          <SelectItem key={p.id} value={String(p.id)}>
                            {p.name}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    </>
                  )}
                </SelectContent>
              </Select>
              {r.source !== "none" && <ConfidenceMeter value={r.confidence} />}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
