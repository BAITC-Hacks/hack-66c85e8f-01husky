import { cn } from "@/lib/utils";

/** Scrolling bar meter of recent RMS levels, mirrored around the center line. */
export function LevelMeter({ levels, active, className }: { levels: number[]; active: boolean; className?: string }) {
  return (
    <div className={cn("flex h-16 items-center gap-[3px]", className)} aria-hidden>
      {levels.map((l, i) => (
        <span
          key={i}
          className={cn("w-[3px] flex-1 rounded-full transition-[height] duration-75", active ? "bg-rec" : "bg-border")}
          style={{ height: `${Math.max(6, l * 100)}%`, opacity: active ? 0.35 + (i / levels.length) * 0.65 : 1 }}
        />
      ))}
    </div>
  );
}
