"use client";

import { useEffect } from "react";
import { ErrorPage } from "@/components/common/error-screen";

/** Uncaught render error outside the app shell (auth pages, root). */
export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => console.error(error), [error]);
  const offline = typeof navigator !== "undefined" && !navigator.onLine;
  return <ErrorPage variant={offline ? "offline" : "crash"} onRetry={reset} digest={error.digest} />;
}
