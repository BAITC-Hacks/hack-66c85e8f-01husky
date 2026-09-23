"use client";

import { AudioWaveform, Loader2, Mic, MicOff, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ParticipantAvatar } from "@/components/common/bits";
import { LevelMeter } from "@/components/common/level-meter";
import { Button } from "@/components/ui/button";
import { useNotify } from "@/hooks/use-notify";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useDeleteVoiceprint, useEnrollVoiceprint } from "@/lib/api/queries/participants";
import type { Participant } from "@/lib/api/types";
import { useRecorder } from "@/lib/audio/use-recorder";
import { cn } from "@/lib/utils";

const SECONDS = 10;

/** Participant card with a 10-second voiceprint recording (spec §8.6). */
export function VoiceprintSheet({
  participant,
  onOpenChange,
}: {
  participant: Participant | null;
  onOpenChange: (o: boolean) => void;
}) {
  const t = useTranslations("participants");
  const te = useTranslations("errors");
  const notify = useNotify();
  const rec = useRecorder({ timeslice: 250 });
  const enroll = useEnrollVoiceprint();
  const remove = useDeleteVoiceprint();
  const stopping = useRef(false);
  const [open, setOpen] = useState(false);

  useEffect(() => setOpen(!!participant), [participant]);

  // auto-stop after 10 s and upload
  useEffect(() => {
    if (rec.state !== "recording" || rec.elapsed < SECONDS || stopping.current || !participant) return;
    stopping.current = true;
    rec.stop().then((blob) =>
      enroll.mutate(
        { id: participant.id, audio: blob },
        {
          onSuccess: () => toast.success(t("enrolled")),
          onSettled: () => {
            stopping.current = false;
            rec.reset();
          },
        },
      ),
    );
  }, [rec, enroll, participant, t]);

  const close = (o: boolean) => {
    if (!o && rec.state === "recording") rec.stop().then(rec.reset);
    setOpen(o);
    onOpenChange(o);
  };

  if (!participant) return null;
  const recording = rec.state === "recording";
  const left = Math.max(0, Math.ceil(SECONDS - rec.elapsed));
  const progress = Math.min(1, rec.elapsed / SECONDS);

  return (
    <Sheet open={open} onOpenChange={close}>
      <SheetContent className="w-full gap-0 sm:max-w-md">
        <SheetHeader className="border-b pb-5">
          <div className="flex items-center gap-3">
            <ParticipantAvatar name={participant.name} />
            <div>
              <SheetTitle className="font-heading text-xl">{participant.name}</SheetTitle>
              <SheetDescription>{participant.position ?? participant.email ?? t("guest")}</SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="grid gap-5 p-4">
          <div className="flex items-center justify-between">
            <span className="text-primary text-xs font-semibold tracking-wide uppercase">
              {t("voiceprint")}
            </span>
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium",
                participant.has_voiceprint
                  ? "border-mint/40 bg-mint/10 text-mint"
                  : "text-muted-foreground border-dashed",
              )}
            >
              <AudioWaveform className="size-3" />
              {participant.has_voiceprint ? t("hasVoiceprint") : t("noVoiceprint")}
            </span>
          </div>

          <p className="text-muted-foreground text-sm">{t("recordHint")}</p>
          <p className="border-primary bg-brand-soft/70 rounded-md border-l-2 px-3 py-2 text-sm italic">
            {t("sample")}
          </p>

          {/* Countdown ring */}
          <div className="flex flex-col items-center py-4">
            <div className="relative size-40">
              <svg viewBox="0 0 100 100" className="size-full -rotate-90">
                <circle cx="50" cy="50" r="44" fill="none" stroke="var(--border)" strokeWidth="4" />
                <circle
                  cx="50"
                  cy="50"
                  r="44"
                  fill="none"
                  stroke={recording ? "var(--rec)" : "var(--brand)"}
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeDasharray={2 * Math.PI * 44}
                  strokeDashoffset={2 * Math.PI * 44 * (1 - progress)}
                  className="transition-[stroke-dashoffset] duration-100"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                {enroll.isPending ? (
                  <Loader2 className="text-primary size-8 animate-spin" />
                ) : recording ? (
                  <>
                    <span className="tabular font-mono text-4xl font-light">{left}</span>
                    <span className="text-muted-foreground text-xs">{t("recording")}</span>
                  </>
                ) : rec.state === "denied" ? (
                  <MicOff className="text-coral size-8" />
                ) : (
                  <Mic className="text-muted-foreground size-8" />
                )}
              </div>
            </div>
            <LevelMeter levels={rec.levels.slice(-32)} active={recording} className="mt-4 h-10 w-56" />
            {enroll.isPending && <p className="text-muted-foreground mt-2 text-sm">{t("enrolling")}</p>}
            {rec.error && <p className="text-coral mt-2 text-sm">{te(`mic.${rec.error}`)}</p>}
          </div>

          <Button
            size="lg"
            className={cn("h-11", !recording && "bg-rec hover:bg-rec/90 text-white")}
            disabled={recording || enroll.isPending}
            onClick={async () => {
              const micErr = await rec.start();
              if (micErr) notify.warn(te(`mic.${micErr}`), te(`mic.${micErr}Hint`));
            }}
          >
            <Mic />
            {participant.has_voiceprint ? t("rerecord") : t("record")}
          </Button>
          {participant.has_voiceprint && (
            <Button
              variant="ghost"
              className="text-coral"
              disabled={remove.isPending || recording}
              onClick={() => remove.mutate(participant.id, { onSuccess: () => toast(t("removed")) })}
            >
              <Trash2 /> {t("removeVoiceprint")}
            </Button>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
