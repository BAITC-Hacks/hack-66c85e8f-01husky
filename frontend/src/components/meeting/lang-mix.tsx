"use client";

import { useTranslations } from "next-intl";

const COLORS: Record<string, string> = {
  ru: "var(--brand)",
  kk: "var(--sun)",
  mixed: "var(--mint)",
  other: "var(--muted-foreground)",
};

/** Share of RU / KZ / mixed ("шала") speech, from language_stats. */
export function LangMix({ stats }: { stats: Record<string, number> }) {
  const t = useTranslations("langName");
  const entries = Object.entries(stats).filter(([, v]) => v > 0);
  return (
    <div className="grid gap-2">
      <div className="flex h-2 overflow-hidden rounded-full bg-muted">
        {entries.map(([k, v]) => (
          <span key={k} style={{ width: `${v * 100}%`, background: COLORS[k] ?? COLORS.other }} />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
        {entries.map(([k, v]) => (
          <span key={k} className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-full" style={{ background: COLORS[k] ?? COLORS.other }} />
            {t.has(k) ? t(k as "ru") : k}
            <span className="font-mono text-muted-foreground">{Math.round(v * 100)}%</span>
          </span>
        ))}
      </div>
    </div>
  );
}
