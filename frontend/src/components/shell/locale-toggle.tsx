"use client";

import { useLocaleSwitch } from "@/hooks/use-locale-switch";
import { locales } from "@/i18n/config";
import { cn } from "@/lib/utils";

const LABEL = { ru: "RU", kk: "ҚАЗ" } as const;

export function LocaleToggle({ persist = true, className }: { persist?: boolean; className?: string }) {
  const { locale, switchTo, pending } = useLocaleSwitch();
  return (
    <div
      role="radiogroup"
      className={cn("inline-flex rounded-md border bg-card p-0.5 font-mono text-[11px]", pending && "opacity-60", className)}
    >
      {locales.map((l) => (
        <button
          key={l}
          role="radio"
          aria-checked={locale === l}
          onClick={() => switchTo(l, persist)}
          className={cn(
            "rounded-[4px] px-2 py-1 font-semibold tracking-wider transition-colors",
            locale === l ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {LABEL[l]}
        </button>
      ))}
    </div>
  );
}
