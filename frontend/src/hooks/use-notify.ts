"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useMemo } from "react";
import { toast } from "sonner";
import { errorKind, isRetryable, serverDetail, type ErrorKind } from "@/lib/api/errors";

/** Kinds that describe the whole session/connection: show one toast, not one per failed request. */
const SINGLETON: ReadonlySet<ErrorKind> = new Set(["network", "unauthorized", "unavailable", "rateLimited"]);

export type NotifyErrorOptions = {
  /** Replaces the generic title, e.g. "Could not download the file". The kind's hint stays as the description. */
  title?: string;
  /** Adds a "Retry" button when the failure looks transient. */
  retry?: () => void;
};

/**
 * One place that turns any failure into a localized toast. Use this instead of
 * `toast.error(e.message)`: raw backend/fetch messages are English and often cryptic.
 */
export function useNotify() {
  const t = useTranslations("errors");
  const router = useRouter();

  return useMemo(() => {
    const error = (err: unknown, opts: NotifyErrorOptions = {}) => {
      const kind = errorKind(err);
      // While the browser is offline, ConnectionStatus already shows a sticky toast.
      if (kind === "network" && typeof navigator !== "undefined" && !navigator.onLine) return;
      const title = opts.title ?? t(`toast.${kind}.title`);
      const description = serverDetail(err, kind) ?? t(`toast.${kind}.hint`);
      const action =
        kind === "unauthorized"
          ? { label: t("actions.login"), onClick: () => router.push("/login") }
          : opts.retry && isRetryable(kind)
            ? { label: t("actions.retry"), onClick: opts.retry }
            : undefined;
      toast.error(title, {
        id: SINGLETON.has(kind) ? `error-${kind}` : undefined,
        description,
        action,
        duration: kind === "unauthorized" ? Infinity : 7000,
      });
    };

    /** A problem that isn't an exception: bad input, missing device, etc. */
    const warn = (title: string, description?: string) => toast.warning(title, { description });

    return { error, warn };
  }, [t, router]);
}
