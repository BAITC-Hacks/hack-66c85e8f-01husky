import { cn } from "@/lib/utils";

/** App mark: rounded gradient tile with a white "Х" and a record dot. */
export function SealMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={cn("size-8", className)} aria-hidden>
      <defs>
        <linearGradient id="hx-mark" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
          <stop stopColor="#7c77ff" />
          <stop offset="1" stopColor="#4f46e5" />
        </linearGradient>
      </defs>
      <rect width="40" height="40" rx="11" fill="url(#hx-mark)" />
      <path d="M13 13L25.5 27M25.5 13L13 27" stroke="#fff" strokeWidth="3.4" strokeLinecap="round" />
      <circle cx="30.5" cy="10" r="3.6" fill="#ff4d5e" stroke="#fff" strokeWidth="1.6" />
    </svg>
  );
}

export function Wordmark({ className, compact = false }: { className?: string; compact?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <SealMark />
      {!compact && <span className="font-heading text-xl font-bold tracking-tight text-foreground">Хаттама</span>}
    </span>
  );
}
