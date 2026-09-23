"use client";

import { FileAudio, Loader2, UploadCloud, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";

const ACCEPT = "audio/*,video/*,.mp3,.wav,.m4a,.ogg,.webm,.mp4,.mkv,.mov";

export function UploadPane({ onSubmit, pending }: { onSubmit: (file: File) => void; pending: boolean }) {
  const t = useTranslations("newMeeting.upload");
  const te = useTranslations("newMeeting.errors");
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const pick = (f: File | undefined | null) => {
    if (!f) return;
    setFile(f);
    setError(null);
  };

  return (
    <div className="grid gap-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          pick(e.dataTransfer.files?.[0]);
        }}
        onClick={() => input.current?.click()}
        className={cn(
          "group relative flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors",
          drag ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-muted/40",
          error && "border-coral/60",
        )}
      >
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => pick(e.target.files?.[0])}
        />
        {file ? (
          <div
            className="bg-card flex w-full max-w-md items-center gap-3 rounded-md border p-3 text-left"
            onClick={(e) => e.stopPropagation()}
          >
            <span className="bg-primary/10 text-primary flex size-10 items-center justify-center rounded-md">
              <FileAudio className="size-5" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate font-medium">{file.name}</span>
              <span className="text-muted-foreground font-mono text-xs">{formatBytes(file.size)}</span>
            </span>
            <Button variant="ghost" size="icon-sm" onClick={() => setFile(null)} aria-label="remove">
              <X />
            </Button>
          </div>
        ) : (
          <>
            <UploadCloud
              className={cn(
                "text-muted-foreground mb-3 size-10 transition-transform group-hover:-translate-y-0.5",
                drag && "text-primary",
              )}
            />
            <p className="font-heading text-lg">{t("drop")}</p>
            <p className="text-muted-foreground mt-1 text-sm">
              {t("or")} <span className="text-primary underline underline-offset-4">{t("browse")}</span>
            </p>
            <p className="text-muted-foreground mt-4 font-mono text-[11px]">{t("formats")}</p>
          </>
        )}
      </div>
      {error && <p className="text-coral text-xs">{error}</p>}
      <Button
        size="lg"
        className="h-11"
        disabled={pending}
        onClick={() => (file ? onSubmit(file) : setError(te("file")))}
      >
        {pending ? <Loader2 className="animate-spin" /> : <UploadCloud />}
        {pending ? t("uploading") : t("submit")}
      </Button>
    </div>
  );
}
