"use client";

import {
  Download,
  FileText,
  Loader2,
  MoreHorizontal,
  RefreshCcw,
  Send,
  Stamp,
  Trash2,
  VolumeX,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useNotify } from "@/hooks/use-notify";
import { downloadFile } from "@/lib/api/download";
import { useDeleteAudio, useDeleteMeeting, useMeetingAction, useSendToSed } from "@/lib/api/queries/meetings";
import type { ExportFormat, Locale, Meeting } from "@/lib/api/types";
import { ConfirmAction } from "./confirm-action";

type Dialog = "confirm" | "reprocess" | "audio" | "delete" | null;

export function ActionsBar({ meeting, onConfirmed }: { meeting: Meeting; onConfirmed: () => void }) {
  const t = useTranslations("meeting.actions");
  const router = useRouter();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [exporting, setExporting] = useState<string | null>(null);
  const confirm = useMeetingAction(meeting.id, "confirm");
  const reprocess = useMeetingAction(meeting.id, "reprocess");
  const sed = useSendToSed(meeting.id);
  const delAudio = useDeleteAudio(meeting.id);
  const delMeeting = useDeleteMeeting();

  const isDraft = meeting.status === "draft";
  const isConfirmed = meeting.status === "confirmed";
  const busy = meeting.status === "processing" || meeting.status === "uploaded";
  const notify = useNotify();
  const te = useTranslations("errors");

  const doExport = async (format: ExportFormat, lang: Locale) => {
    const key = `${format}-${lang}`;
    setExporting(key);
    try {
      await downloadFile(
        `/meetings/${meeting.id}/export`,
        { format, lang },
        `protocol-${meeting.id}.${format}`,
      );
    } catch (e) {
      notify.error(e, { title: te("download.failed"), retry: () => doExport(format, lang) });
    } finally {
      setExporting(null);
    }
  };

  const exportMenu = (format: ExportFormat) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" disabled={busy || !!exporting}>
          {exporting?.startsWith(format) ? (
            <Loader2 className="animate-spin" />
          ) : format === "pdf" ? (
            <Download />
          ) : (
            <FileText />
          )}
          {t(format)}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel className="text-muted-foreground text-xs">{t("exportLang")}</DropdownMenuLabel>
        <DropdownMenuItem onClick={() => doExport(format, "ru")}>
          Русский · {format.toUpperCase()}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => doExport(format, "kk")}>
          Қазақша · {format.toUpperCase()}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );

  return (
    <div className="flex flex-wrap items-center gap-2">
      {isDraft && (
        <Button size="lg" onClick={() => setDialog("confirm")} disabled={confirm.isPending}>
          {confirm.isPending ? <Loader2 className="animate-spin" /> : <Stamp />}
          {t("confirm")}
        </Button>
      )}
      {exportMenu("docx")}
      {exportMenu("pdf")}
      {isConfirmed && (
        <Button
          variant={meeting.sed_ref ? "ghost" : "secondary"}
          disabled={sed.isPending}
          onClick={() =>
            sed.mutate(undefined, {
              onSuccess: (r) => toast.success(t("sedDone"), { description: `${t("sedRef")}: ${r.sed_ref}` }),
            })
          }
        >
          {sed.isPending ? <Loader2 className="animate-spin" /> : <Send />}
          {meeting.sed_ref ? <span className="font-mono text-xs">{meeting.sed_ref}</span> : t("sed")}
        </Button>
      )}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" aria-label={t("more")}>
            <MoreHorizontal />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuItem disabled={busy || !meeting.has_audio} onClick={() => setDialog("reprocess")}>
            <RefreshCcw /> {t("reprocess")}
          </DropdownMenuItem>
          <DropdownMenuItem disabled={!meeting.has_audio} onClick={() => setDialog("audio")}>
            <VolumeX /> {t("deleteAudio")}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive" onClick={() => setDialog("delete")}>
            <Trash2 /> {t("delete")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <ConfirmAction
        open={dialog === "confirm"}
        onOpenChange={(o) => !o && setDialog(null)}
        title={t("confirmTitle")}
        body={t("confirmBody")}
        actionLabel={t("confirm")}
        onConfirm={() =>
          confirm.mutate(undefined, {
            onSuccess: () => {
              toast.success(t("confirmed"));
              onConfirmed();
            },
          })
        }
      />
      <ConfirmAction
        open={dialog === "reprocess"}
        onOpenChange={(o) => !o && setDialog(null)}
        title={t("reprocessTitle")}
        body={t("reprocessBody")}
        actionLabel={t("reprocess")}
        onConfirm={() => reprocess.mutate()}
      />
      <ConfirmAction
        open={dialog === "audio"}
        onOpenChange={(o) => !o && setDialog(null)}
        title={t("deleteAudioTitle")}
        body={t("deleteAudioBody")}
        actionLabel={t("deleteAudio")}
        destructive
        onConfirm={() => delAudio.mutate(undefined, { onSuccess: () => toast(t("audioDeleted")) })}
      />
      <ConfirmAction
        open={dialog === "delete"}
        onOpenChange={(o) => !o && setDialog(null)}
        title={t("delete")}
        body={meeting.title}
        actionLabel={t("delete")}
        destructive
        onConfirm={() => delMeeting.mutate(meeting.id, { onSuccess: () => router.replace("/meetings") })}
      />
    </div>
  );
}
