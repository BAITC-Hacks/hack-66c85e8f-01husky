"use client";

import { useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import { useEffect, type ReactNode } from "react";
import { setLocaleCookie } from "@/hooks/use-locale-switch";
import { isLocale } from "@/i18n/config";
import { ApiError } from "@/lib/api/client";
import { useMe } from "@/lib/api/queries/auth";
import type { User } from "@/lib/api/types";
import { SealMark } from "@/components/brand/wordmark";

/** Client-side guard: 401 from /auth/me → /login. Also applies users.locale once. */
export function AuthGuard({ children }: { children: (user: User) => ReactNode }) {
  const { data: user, error, isLoading } = useMe();
  const router = useRouter();
  const locale = useLocale();

  useEffect(() => {
    if (error instanceof ApiError && error.status === 401) router.replace("/login");
  }, [error, router]);

  useEffect(() => {
    // Apply users.locale once per session (right after login); later the
    // header toggle is the source of truth.
    if (!user || sessionStorage.getItem("locale-synced")) return;
    sessionStorage.setItem("locale-synced", "1");
    if (!isLocale(user.locale) || user.locale === locale) return;
    setLocaleCookie(user.locale);
    router.refresh();
  }, [user, locale, router]);

  if (isLoading || !user) {
    return (
      <div className="text-primary flex min-h-svh items-center justify-center">
        <SealMark className="size-12 animate-pulse" />
      </div>
    );
  }
  return <>{children(user)}</>;
}
