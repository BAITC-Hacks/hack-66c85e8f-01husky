"use client";

import { Loader2, Mic, MicOff, Square } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { LevelMeter } from "@/components/common/level-meter";
import { Button } from "@/components/ui/button";
import { openLiveSocket, type LiveSocket } from "@/lib/api/client";
import { useRecorder } from "@/lib/audio/use-recorder";
import { formatBytes, formatTimecode } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Live recording: POST /meetings/live → WS /meetings/{id}/live,
 * binary webm/opus chunks every second, {"event":"stop"} to finish (spec §7).
 */
export function RecordPane({
  createMeeting,
  onDone,
}: {
  /** validates the common form and creates the live meeting; null if invalid */
  createMeeting: () => Promise<number | null>;
  onDone: (id: number) => void;
}) {
  const t = useTranslations("newMeeting.record");
  const socket = useRef<LiveSocket | null>(null);
  const meetingId = useRef<number | null>(null);
  const [phase, setPhase] = useState<"idle" | "connecting" | "live" | "stopping">("idle");
  const rec = useRecorder({
    timeslice: 1000,
    onChunk: (b) => {
      if (socket.current?.readyState === WebSocket.OPEN) socket.current.send(b);
    },
  });

  const start = async () => {
    setPhase("connecting");
    const id = await createMeeting();
    if (!id) {
      setPhase("idle");
      return;
    }
    meetingId.current = id;
    const ws = await openLiveSocket(id);
    ws.binaryType = "blob";
    socket.current = ws;
    ws.onerror = () => toast.error("WebSocket error");
    ws.onopen = async () => {
      await rec.start();
      setPhase("live");
    };
  };

  const stop = async () => {
    setPhase("stopping");
    await rec.stop();
    const ws = socket.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ event: "stop" }));
      await new Promise<void>((resolve) => {
        const timer = setTimeout(resolve, 2500);
        ws.onclose = () => {
          clearTimeout(timer);
          resolve();
        };
      });
    }
    if (meetingId.current) onDone(meetingId.current);
  };

  const live = phase === "live";

  return (
    <div className="grid gap-5">
      {/* Mandatory consent banner (spec §8.3) */}
      <div
        className={cn(
          "flex items-start gap-3 rounded-lg border px-4 py-3 transition-colors",
          live ? "border-rec/40 bg-rec/10 text-rec" : "border-border bg-muted/50 text-muted-foreground",
        )}
        role="status"
      >
        <span className={cn("mt-1.5 size-2.5 shrink-0 rounded-full bg-current", live && "animate-rec")} />
        <div>
          <p className="font-semibold">{t("banner")}</p>
          <p className="text-sm opacity-80">{t("bannerHint")}</p>
        </div>
      </div>

      <div className="flex flex-col items-center rounded-lg border bg-card px-6 py-8">
        <div className={cn("font-mono text-6xl font-light tracking-tight tabular", live ? "text-foreground" : "text-muted-foreground/50")}>
          {formatTimecode(rec.elapsed)}
        </div>
        <LevelMeter levels={rec.levels} active={live} className="mt-6 w-full max-w-md" />
        <div className="mt-3 h-4 font-mono text-[11px] text-muted-foreground">
          {live && t("sent", { size: formatBytes(rec.bytes) })}
          {rec.state === "denied" && (
            <span className="inline-flex items-center gap-1 text-brick">
              <MicOff className="size-3" /> {t("micDenied")}
            </span>
          )}
        </div>
      </div>

      {live || phase === "stopping" ? (
        <Button size="lg" variant="destructive" className="h-11" onClick={stop} disabled={phase === "stopping"}>
          {phase === "stopping" ? <Loader2 className="animate-spin" /> : <Square className="fill-current" />}
          {t("stop")}
        </Button>
      ) : (
        <Button size="lg" className="h-11 bg-rec text-white hover:bg-rec/90" onClick={start} disabled={phase === "connecting"}>
          {phase === "connecting" ? <Loader2 className="animate-spin" /> : <Mic />}
          {phase === "connecting" ? t("connecting") : t("start")}
        </Button>
      )}
    </div>
  );
}
