"use client";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useRef, useState, type ReactNode } from "react";
import { ConnectionStatus } from "@/components/shell/connection-status";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useNotify } from "@/hooks/use-notify";
import { ApiError } from "@/lib/api/client";
import { errorKind } from "@/lib/api/errors";

declare module "@tanstack/react-query" {
  interface Register {
    /** `silent`: the caller shows its own error UI, skip the global toast. */
    queryMeta: { silent?: boolean };
    mutationMeta: { silent?: boolean };
  }
}

export function Providers({ children }: { children: ReactNode }) {
  const notify = useNotify();
  // The QueryClient is created once; read the latest notify (locale may change) through a ref.
  const notifyRef = useRef(notify);
  notifyRef.current = notify;

  const [client] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({
          // A failed first load renders inline (<QueryError>). Only a failed background
          // refetch, where stale data is still on screen, needs a toast.
          onError: (err, query) => {
            if (query.meta?.silent || query.state.data === undefined) return;
            notifyRef.current.error(err, { retry: () => query.fetch() });
          },
        }),
        // Every failed mutation gets a toast unless it opts out with meta.silent.
        mutationCache: new MutationCache({
          onError: (err, variables, _ctx, mutation) => {
            if (mutation.meta?.silent) return;
            // Only offer a retry when the request surely didn't land, so creates aren't duplicated.
            const kind = errorKind(err);
            const safe = kind === "network" || kind === "unavailable" || kind === "rateLimited";
            notifyRef.current.error(err, { retry: safe ? () => mutation.execute(variables) : undefined });
          },
        }),
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: (count, err) =>
              !(err instanceof ApiError && err.status < 500 && err.status > 0) && count < 2,
          },
        },
      }),
  );

  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={client}>
        <TooltipProvider delayDuration={200}>
          {children}
          <Toaster position="bottom-right" richColors closeButton />
          <ConnectionStatus />
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
