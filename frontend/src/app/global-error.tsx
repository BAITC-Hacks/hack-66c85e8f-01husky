"use client";

import { NextIntlClientProvider } from "next-intl";
import { useEffect } from "react";
import { ErrorPage } from "@/components/common/error-screen";
import { defaultLocale, isLocale, LOCALE_COOKIE } from "@/i18n/config";
import kk from "../../messages/kk.json";
import ru from "../../messages/ru.json";
import "./globals.css";

/**
 * Last resort: the root layout itself crashed, so there are no providers.
 * Rebuild the minimum (html/body, messages from the locale cookie) and show the crash screen.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => console.error(error), [error]);
  const raw =
    typeof document !== "undefined"
      ? document.cookie.match(new RegExp(`(?:^|; )${LOCALE_COOKIE}=([^;]*)`))?.[1]
      : undefined;
  const locale = isLocale(raw) ? raw : defaultLocale;
  return (
    <html lang={locale}>
      <body className="antialiased">
        <NextIntlClientProvider locale={locale} messages={locale === "kk" ? kk : ru}>
          <ErrorPage variant="crash" onRetry={reset} digest={error.digest} />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
