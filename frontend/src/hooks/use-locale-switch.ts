"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import { useCallback, useTransition } from "react";
import { qk } from "@/lib/api/queries/keys";
import type { User } from "@/lib/api/types";
import { LOCALE_COOKIE, type AppLocale } from "@/i18n/config";

export function setLocaleCookie(locale: AppLocale) {
  document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=31536000; samesite=lax`;
}

/** Switch UI locale: cookie + server re-render. The backend has no endpoint to persist users.locale. */
export function useLocaleSwitch() {
  const router = useRouter();
  const current = useLocale() as AppLocale;
  const qc = useQueryClient();
  const [pending, start] = useTransition();
  const switchTo = useCallback(
    (locale: AppLocale, persist = true) => {
      if (locale === current) return;
      setLocaleCookie(locale);
      if (persist) {
        qc.setQueryData<User>(qk.me, (u) => (u ? { ...u, locale } : u));
      }
      start(() => router.refresh());
    },
    [current, router, qc],
  );
  return { locale: current, switchTo, pending };
}
