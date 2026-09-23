"use client";

import { Bot, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Field } from "@/components/common/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Platform } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const PLATFORMS: { id: Platform; host: RegExp; mark: string }[] = [
  { id: "meet", host: /meet\.google\.com/, mark: "M" },
  { id: "zoom", host: /zoom\.(us|com)/, mark: "Z" },
  { id: "teams", host: /teams\.(microsoft|live)\.com/, mark: "T" },
];

export function BotPane({ onSubmit, pending }: { onSubmit: (v: { platform: Platform; url: string }) => void; pending: boolean }) {
  const t = useTranslations("newMeeting");
  const tp = useTranslations("platform");
  const [platform, setPlatform] = useState<Platform>("meet");
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  const onUrl = (v: string) => {
    setUrl(v);
    setError(null);
    const hit = PLATFORMS.find((p) => p.host.test(v));
    if (hit) setPlatform(hit.id);
  };

  const submit = () => {
    try {
      const u = new URL(url);
      if (!/^https?:$/.test(u.protocol)) throw new Error();
    } catch {
      setError(t("errors.url"));
      return;
    }
    onSubmit({ platform, url });
  };

  return (
    <div className="grid gap-5">
      <Field label={t("fields.platform")}>
        <div role="radiogroup" className="grid grid-cols-3 gap-2">
          {PLATFORMS.map((p) => (
            <button
              key={p.id}
              type="button"
              role="radio"
              aria-checked={platform === p.id}
              onClick={() => setPlatform(p.id)}
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border bg-card px-3 py-4 text-sm transition-all",
                platform === p.id ? "border-primary ring-2 ring-primary/20" : "hover:border-primary/40",
              )}
            >
              <span
                className={cn(
                  "flex size-9 items-center justify-center rounded-md font-heading text-lg font-semibold",
                  platform === p.id ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
                )}
              >
                {p.mark}
              </span>
              {tp(p.id)}
            </button>
          ))}
        </div>
      </Field>
      <Field label={t("fields.url")} htmlFor="bot-url" error={error ?? undefined}>
        <Input
          id="bot-url"
          value={url}
          onChange={(e) => onUrl(e.target.value)}
          placeholder={t("fields.urlPlaceholder")}
          className="h-10 font-mono text-sm"
          aria-invalid={!!error}
        />
      </Field>
      <p className="rounded-md border border-dashed bg-muted/40 p-3 text-sm text-muted-foreground">{t("bot.hint")}</p>
      <Button size="lg" className="h-11" onClick={submit} disabled={pending}>
        {pending ? <Loader2 className="animate-spin" /> : <Bot />}
        {t("bot.submit")}
      </Button>
    </div>
  );
}
