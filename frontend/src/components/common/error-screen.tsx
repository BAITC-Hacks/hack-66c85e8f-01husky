"use client";

import {
  ArrowLeft,
  Bug,
  Check,
  Copy,
  FileQuestion,
  KeyRound,
  LogIn,
  RotateCw,
  SearchX,
  ServerCrash,
  ServerOff,
  ShieldX,
  WifiOff,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { Wordmark } from "@/components/brand/wordmark";
import { Button } from "@/components/ui/button";
import { errorKind, type ErrorKind } from "@/lib/api/errors";
import { cn } from "@/lib/utils";

export type ErrorVariant =
  | "notFound"
  | "meetingNotFound"
  | "forbidden"
  | "unauthorized"
  | "server"
  | "unavailable"
  | "offline"
  | "crash";

const VISUAL: Record<ErrorVariant, { icon: LucideIcon; code?: string; tone: "brand" | "coral" | "sun" }> = {
  notFound: { icon: SearchX, code: "404", tone: "brand" },
  meetingNotFound: { icon: FileQuestion, code: "404", tone: "brand" },
  forbidden: { icon: ShieldX, code: "403", tone: "sun" },
  unauthorized: { icon: KeyRound, code: "401", tone: "sun" },
  server: { icon: ServerCrash, code: "500", tone: "coral" },
  unavailable: { icon: ServerOff, code: "503", tone: "sun" },
  offline: { icon: WifiOff, tone: "sun" },
  crash: { icon: Bug, tone: "coral" },
};

const TONE = {
  brand: "bg-brand-soft text-primary",
  coral: "bg-coral/10 text-coral",
  sun: "bg-sun-soft text-sun",
};

/** Which screen to show for a failed request. */
export function variantFor(kind: ErrorKind): ErrorVariant {
  switch (kind) {
    case "network":
      return "offline";
    case "unauthorized":
      return "unauthorized";
    case "forbidden":
      return "forbidden";
    case "notFound":
      return "notFound";
    case "unavailable":
    case "rateLimited":
      return "unavailable";
    default:
      return "server";
  }
}

/**
 * Full error state: icon, code, localized title/hint and the actions that make
 * sense for the variant. Used by the route error pages and for failed queries.
 */
export function ErrorScreen({
  variant,
  onRetry,
  digest,
  actions,
  className,
}: {
  variant: ErrorVariant;
  /** Shown as the primary "Retry" button for transient variants. Without it, "Reload" reloads the page. */
  onRetry?: () => void;
  /** Next.js error digest, shown so users can quote it to the admin. */
  digest?: string;
  /** Replaces the default buttons. */
  actions?: ReactNode;
  className?: string;
}) {
  const t = useTranslations("errors");
  const router = useRouter();
  const { icon: Icon, code, tone } = VISUAL[variant];

  const home = (
    <Button asChild variant="outline" key="home">
      <Link href="/meetings">{t("actions.home")}</Link>
    </Button>
  );
  const back = (
    <Button variant="ghost" key="back" onClick={() => router.back()}>
      <ArrowLeft data-icon="inline-start" />
      {t("actions.back")}
    </Button>
  );
  const retry = (
    <Button key="retry" onClick={onRetry ?? (() => window.location.reload())}>
      <RotateCw data-icon="inline-start" />
      {onRetry ? t("actions.retry") : t("actions.reload")}
    </Button>
  );
  const login = (
    <Button asChild key="login">
      <Link href="/login">
        <LogIn data-icon="inline-start" />
        {t("actions.login")}
      </Link>
    </Button>
  );

  const defaults: Record<ErrorVariant, ReactNode[]> = {
    notFound: [home, back],
    meetingNotFound: [home, back],
    forbidden: [home, back],
    unauthorized: [login],
    server: [retry, home],
    unavailable: [retry, home],
    offline: [retry],
    crash: [retry, home],
  };

  return (
    <div
      role="alert"
      className={cn("flex flex-col items-center px-4 py-16 text-center sm:py-24", className)}
    >
      <span className={cn("mb-6 flex size-16 items-center justify-center rounded-2xl", TONE[tone])}>
        <Icon className="size-7" />
      </span>
      {code && (
        <span className="text-primary mb-2 text-xs font-semibold tracking-wide uppercase">
          {t("code")} <span className="font-mono">{code}</span>
        </span>
      )}
      <h1 className="font-heading text-2xl font-bold text-balance sm:text-3xl">{t(`pages.${variant}.title`)}</h1>
      <p className="text-muted-foreground mt-2 max-w-md text-balance">{t(`pages.${variant}.hint`)}</p>
      <div className="mt-8 flex flex-wrap items-center justify-center gap-2">
        {actions ?? defaults[variant]}
      </div>
      {digest && <DigestChip digest={digest} />}
    </div>
  );
}

function DigestChip({ digest }: { digest: string }) {
  const t = useTranslations("errors");
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={() =>
        navigator.clipboard?.writeText(digest).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        })
      }
      className="text-muted-foreground hover:text-foreground mt-6 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-mono text-[11px] transition-colors"
      title={t("actions.copy")}
    >
      {copied ? <Check className="text-mint size-3" /> : <Copy className="size-3" />}
      {copied ? t("actions.copied") : `${t("code")}: ${digest}`}
    </button>
  );
}

/** Inline state for a query that failed to load. `notFound` lets a page use a more specific 404. */
export function QueryError({
  error,
  onRetry,
  notFound = "notFound",
}: {
  error: unknown;
  onRetry?: () => void;
  notFound?: Extract<ErrorVariant, "notFound" | "meetingNotFound">;
}) {
  const variant = variantFor(errorKind(error));
  return (
    <ErrorScreen
      variant={variant === "notFound" ? notFound : variant}
      onRetry={onRetry}
      className="bg-card/60 rounded-2xl border border-dashed py-12 sm:py-16"
    />
  );
}

/** Standalone page frame (no app shell): logo on top, the error centered. */
export function ErrorPage(props: React.ComponentProps<typeof ErrorScreen>) {
  return (
    <div className="bg-paper flex min-h-svh flex-col">
      <header className="mx-auto flex w-full max-w-7xl items-center px-4 py-5 sm:px-6">
        <Link href="/meetings" aria-label="Kenes AI">
          <Wordmark />
        </Link>
      </header>
      <main className="flex flex-1 items-center justify-center pb-16">
        <ErrorScreen {...props} />
      </main>
    </div>
  );
}
