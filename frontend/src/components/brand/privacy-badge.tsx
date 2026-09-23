"use client";

import { ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/** "Data never leaves the perimeter", the key selling point of spec §2. */
export function PrivacyBadge({ modelInfo, className }: { modelInfo?: Record<string, string> | null; className?: string }) {
  const t = useTranslations("privacy");
  const badge = (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-sage/40 bg-sage/10 px-2.5 py-1 text-xs font-medium text-sage",
        className,
      )}
    >
      <ShieldCheck className="size-3.5" />
      {t("badge")}
      <span className="font-mono text-[10px] uppercase opacity-70">· {t("onprem")}</span>
    </span>
  );
  if (!modelInfo) return badge;
  return (
    <Tooltip>
      <TooltipTrigger asChild>{badge}</TooltipTrigger>
      <TooltipContent className="max-w-xs">
        <p className="mb-1 font-medium">{t("models")}</p>
        <ul className="space-y-0.5 font-mono text-[11px]">
          {Object.entries(modelInfo).map(([k, v]) => (
            <li key={k}>
              <span className="opacity-60">{k}:</span> {v}
            </li>
          ))}
        </ul>
      </TooltipContent>
    </Tooltip>
  );
}
