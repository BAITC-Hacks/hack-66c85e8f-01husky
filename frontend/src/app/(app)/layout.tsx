"use client";

import { PrivacyBadge } from "@/components/brand/privacy-badge";
import { SealMark } from "@/components/brand/wordmark";
import { AppHeader } from "@/components/shell/app-header";
import { AuthGuard } from "@/components/shell/auth-guard";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      {(user) => (
        <div className="flex min-h-svh flex-col">
          <AppHeader user={user} />
          <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 sm:py-10">{children}</main>
          <footer className="border-t">
            <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4 text-xs text-muted-foreground sm:px-6">
              <span className="inline-flex items-center gap-2">
                <SealMark className="size-4 text-primary" />
                Хаттама · 2026
              </span>
              <PrivacyBadge />
            </div>
          </footer>
        </div>
      )}
    </AuthGuard>
  );
}
