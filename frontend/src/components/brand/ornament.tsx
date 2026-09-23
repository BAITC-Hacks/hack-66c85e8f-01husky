import { cn } from "@/lib/utils";
import { useId } from "react";

/** One qoshqar-muiz (ram's horn) motif: two spirals curling out of a stem. */
export function HornMotif({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 22" fill="none" className={className} aria-hidden>
      <path
        d="M20 21V13M20 13C20 7 15 3.5 10 4.5C5.5 5.5 5 11 8.5 12.5C11 13.5 13 11.5 11.5 9.5M20 13C20 7 25 3.5 30 4.5C34.5 5.5 35 11 31.5 12.5C29 13.5 27 11.5 28.5 9.5"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** Hairline rule with a central horn motif, for section breaks. */
export function OrnamentDivider({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-3 text-gold", className)} aria-hidden>
      <span className="h-px flex-1 bg-gradient-to-r from-transparent to-border" />
      <HornMotif className="h-4 w-8 opacity-80" />
      <span className="h-px flex-1 bg-gradient-to-l from-transparent to-border" />
    </div>
  );
}

/** Repeating ornament band (login panel, empty states). */
export function OrnamentBand({ className }: { className?: string }) {
  const id = useId();
  return (
    <svg className={cn("h-6 w-full", className)} aria-hidden>
      <defs>
        <pattern id={id} width="48" height="24" patternUnits="userSpaceOnUse">
          <path
            d="M24 23V15M24 15C24 9 19 5.5 14 6.5C9.5 7.5 9 13 12.5 14.5C15 15.5 17 13.5 15.5 11.5M24 15C24 9 29 5.5 34 6.5C38.5 7.5 39 13 35.5 14.5C33 15.5 31 13.5 32.5 11.5M0 23H48"
            stroke="currentColor"
            strokeWidth="1.1"
            fill="none"
            strokeLinecap="round"
          />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  );
}
