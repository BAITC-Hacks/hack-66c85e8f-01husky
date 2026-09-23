"use client";

import { useEffect } from "react";
import { ErrorScreen } from "@/components/common/error-screen";

/** Uncaught render error inside the app: the header and footer stay, only the page area is replaced. */
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => console.error(error), [error]);
  const offline = typeof navigator !== "undefined" && !navigator.onLine;
  return <ErrorScreen variant={offline ? "offline" : "crash"} onRetry={reset} digest={error.digest} />;
}
