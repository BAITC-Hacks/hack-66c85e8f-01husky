import { ApiError, NETWORK_ERROR, TIMEOUT_ERROR } from "./client";

/** What went wrong, from the user's point of view. Each kind has copy under `errors.toast.<kind>`. */
export type ErrorKind =
  | "network"
  | "timeout"
  | "unauthorized"
  | "forbidden"
  | "notFound"
  | "conflict"
  | "validation"
  | "tooLarge"
  | "unsupported"
  | "rateLimited"
  | "server"
  | "unavailable"
  | "unknown";

export function errorKind(err: unknown): ErrorKind {
  if (typeof navigator !== "undefined" && navigator.onLine === false) return "network";
  if (!(err instanceof ApiError)) return err instanceof TypeError ? "network" : "unknown";
  const s = err.status;
  if (s === NETWORK_ERROR) return "network";
  if (s === TIMEOUT_ERROR || s === 504) return "timeout";
  if (s === 401) return "unauthorized";
  if (s === 403) return "forbidden";
  if (s === 404 || s === 410) return "notFound";
  if (s === 409) return "conflict";
  if (s === 413) return "tooLarge";
  if (s === 415) return "unsupported";
  if (s === 429) return "rateLimited";
  if (s === 400 || s === 422) return "validation";
  if (s === 502 || s === 503) return "unavailable";
  if (s >= 500) return "server";
  return "unknown";
}

/** Kinds where the backend's `detail` is written for humans and worth showing as-is. */
const SHOW_DETAIL: ReadonlySet<ErrorKind> = new Set(["validation", "conflict", "forbidden", "notFound"]);

/** The server's own message, when it's safe and useful to show it. */
export function serverDetail(err: unknown, kind = errorKind(err)): string | undefined {
  if (!(err instanceof ApiError) || !SHOW_DETAIL.has(kind)) return undefined;
  const d = err.detail?.trim();
  return d && d.length <= 200 ? d : undefined;
}

/** Transient failures where "try again" is a sensible action. */
export function isRetryable(kind: ErrorKind): boolean {
  return (
    kind === "network" ||
    kind === "timeout" ||
    kind === "server" ||
    kind === "unavailable" ||
    kind === "rateLimited"
  );
}
