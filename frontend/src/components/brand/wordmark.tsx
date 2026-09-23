import { cn } from "@/lib/utils";

/** Round seal monogram "Х" with a horn crest. */
export function SealMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={cn("size-8", className)} aria-hidden>
      <circle cx="20" cy="20" r="18.5" fill="none" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="20" cy="20" r="15" fill="none" stroke="currentColor" strokeWidth="0.6" strokeDasharray="1.5 2" />
      <path d="M13.5 13.5L26.5 27.5M26.5 13.5L13.5 27.5" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
      <path
        d="M20 9.5C20 7.5 18 6.2 16.3 6.8M20 9.5C20 7.5 22 6.2 23.7 6.8"
        stroke="var(--gold)"
        strokeWidth="1.2"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function Wordmark({ className, compact = false }: { className?: string; compact?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5 text-primary", className)}>
      <SealMark />
      {!compact && (
        <span className="font-heading text-xl font-semibold tracking-tight text-foreground">Хаттама</span>
      )}
    </span>
  );
}
