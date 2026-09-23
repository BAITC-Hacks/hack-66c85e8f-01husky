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
      className={cn("inline-flex rounded-full border bg-card p-0.5 text-[11px]", pending && "opacity-60", className)}
    >
      {locales.map((l) => (
        <button
          key={l}
          role="radio"
          aria-checked={locale === l}
          onClick={() => switchTo(l, persist)}
          className={cn(
            "rounded-full px-2.5 py-1 font-semibold tracking-wide transition-colors",
            locale === l ? "bg-primary text-primary-foreground shadow-soft" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {LABEL[l]}
        </button>
      ))}
    </div>
  );
}
