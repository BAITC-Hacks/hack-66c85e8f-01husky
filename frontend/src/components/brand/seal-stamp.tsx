import { cn } from "@/lib/utils";
import { useId } from "react";

/**
 * Official round stamp, the "approved" moment of a protocol.
 * `animate` plays the stamp-in motion once (on confirm).
 */
export function SealStamp({
  label,
  date,
  refNo,
  animate = false,
  className,
}: {
  label: string;
  date: string;
  refNo?: string | null;
  animate?: boolean;
  className?: string;
}) {
  const id = useId();
  const ring = `${label} · ${label} · `;
  return (
    <div
      className={cn(
        "text-primary pointer-events-none mix-blend-multiply select-none dark:mix-blend-screen",
        animate ? "animate-stamp" : "-rotate-12",
        className,
      )}
      aria-label={label}
      role="img"
    >
      <svg viewBox="0 0 120 120" className="size-full">
        <defs>
          <path id={id} d="M60 60m-45 0a45 45 0 1 1 90 0a45 45 0 1 1 -90 0" />
          <filter id={`${id}-rough`}>
            <feTurbulence type="fractalNoise" baseFrequency="1.2" numOctaves="1" result="n" />
            <feDisplacementMap in="SourceGraphic" in2="n" scale="1.6" />
          </filter>
        </defs>
        <g filter={`url(#${id}-rough)`} opacity="0.85">
          <circle cx="60" cy="60" r="56" fill="none" stroke="currentColor" strokeWidth="2.5" />
          <circle cx="60" cy="60" r="36" fill="none" stroke="currentColor" strokeWidth="1.2" />
          <text fontSize="8.4" fontWeight="700" letterSpacing="1.2" fill="currentColor" className="font-sans">
            <textPath href={`#${id}`}>{ring.slice(0, 42)}</textPath>
          </text>
          <text
            x="60"
            y="56"
            textAnchor="middle"
            fontSize="11"
            fontWeight="700"
            fill="currentColor"
            className="font-mono"
          >
            {date}
          </text>
          {refNo && (
            <text x="60" y="70" textAnchor="middle" fontSize="6.2" fill="currentColor" className="font-mono">
              {refNo}
            </text>
          )}
          <path
            d="M60 82V78M60 78C60 75 57.5 73.5 55 74C53 74.5 52.8 77 54.3 77.6M60 78C60 75 62.5 73.5 65 74C67 74.5 67.2 77 65.7 77.6"
            stroke="currentColor"
            strokeWidth="1.1"
            fill="none"
          />
        </g>
      </svg>
    </div>
  );
}
