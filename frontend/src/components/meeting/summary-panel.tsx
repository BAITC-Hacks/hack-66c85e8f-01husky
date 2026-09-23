"use client";

import { Pencil } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { usePatchMeeting } from "@/lib/api/queries/meetings";

export function Markdown({ children }: { children: string }) {
  return (
    <div className="text-[15px] leading-relaxed">
      <ReactMarkdown
        components={{
          h1: (p) => <h3 className="font-heading mt-5 mb-2 text-lg font-semibold first:mt-0" {...p} />,
          h2: (p) => (
            <h3
              className="text-primary after:bg-border mt-6 mb-2 flex items-center gap-2 text-xs font-semibold tracking-wide uppercase after:h-px after:flex-1 first:mt-0"
              {...p}
            />
          ),
          h3: (p) => <h4 className="mt-4 mb-1 font-semibold" {...p} />,
          p: (p) => <p className="my-2" {...p} />,
          ul: (p) => <ul className="marker:text-primary my-2 list-disc space-y-1 pl-5" {...p} />,
          ol: (p) => (
            <ol
              className="marker:text-muted-foreground my-2 list-decimal space-y-1 pl-5 marker:font-mono marker:text-xs"
              {...p}
            />
          ),
          strong: (p) => <strong className="text-foreground font-semibold" {...p} />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}

export function SummaryPanel({
  meetingId,
  summary,
  editable,
}: {
  meetingId: number;
  summary: string | null;
  editable: boolean;
}) {
  const t = useTranslations("meeting");
  const tc = useTranslations("common");
  const patch = usePatchMeeting(meetingId);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(summary ?? "");

  if (editing) {
    return (
      <div className="grid gap-3">
        <Textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="min-h-[420px] font-mono text-sm leading-relaxed"
          autoFocus
        />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setEditing(false)}>
            {tc("cancel")}
          </Button>
          <Button
            disabled={patch.isPending}
            onClick={() =>
              patch.mutate(
                { summary: draft },
                {
                  onSuccess: () => {
                    toast.success(tc("saved"));
                    setEditing(false);
                  },
                  onError: (e) => toast.error(e.message),
                },
              )
            }
          >
            {tc("save")}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card shadow-soft relative rounded-xl border p-5">
      {editable && (
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-3 right-3"
          onClick={() => {
            setDraft(summary ?? "");
            setEditing(true);
          }}
        >
          <Pencil /> {t("editSummary")}
        </Button>
      )}
      {summary ? (
        <Markdown>{summary}</Markdown>
      ) : (
        <p className="text-muted-foreground text-sm">{t("summaryEmpty")}</p>
      )}
    </div>
  );
}
