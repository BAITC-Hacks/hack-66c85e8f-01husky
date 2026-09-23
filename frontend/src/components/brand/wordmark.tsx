import { cn } from "@/lib/utils";

/** App mark: rounded brand tile with a white "Х" and a record dot (no SVG ids: rendered several times per page). */
export function SealMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={cn("size-8", className)} aria-hidden>
      <rect width="40" height="40" rx="11" fill="var(--brand)" />
      <path d="M0 11C0 4.9 4.9 0 11 0h18c6.1 0 11 4.9 11 11v6C26 23 12 10 0 22z" fill="#fff" opacity="0.14" />
      <path d="M13 13L25.5 27M25.5 13L13 27" stroke="#fff" strokeWidth="3.4" strokeLinecap="round" />
      <circle cx="30.5" cy="10" r="3.6" fill="#ff4d5e" stroke="#fff" strokeWidth="1.6" />
    </svg>
  );
}

export function Wordmark({ className, compact = false }: { className?: string; compact?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <SealMark />
      {!compact && (
        <span className="font-heading text-foreground text-xl font-bold tracking-tight">Хаттама</span>
      )}
    </span>
  );
}
