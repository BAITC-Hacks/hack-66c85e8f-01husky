import { Bot, FileAudio, Mic } from "lucide-react";
import type { MeetingSource } from "@/lib/api/types";

export const SOURCE_ICON: Record<MeetingSource, typeof Mic> = { upload: FileAudio, live: Mic, bot: Bot };

export function SourceIcon({ source, className }: { source: MeetingSource; className?: string }) {
  const Icon = SOURCE_ICON[source];
  return <Icon className={className} />;
}
