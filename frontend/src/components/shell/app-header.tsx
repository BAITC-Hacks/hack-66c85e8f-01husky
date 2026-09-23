"use client";

import { ClipboardList, Compass, LogOut, Menu, UsersRound, Video } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Wordmark } from "@/components/brand/wordmark";
import { ParticipantAvatar } from "@/components/common/bits";
import { NotificationBell } from "@/components/notifications/bell";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { useLogout } from "@/lib/api/queries/auth";
import type { User } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { LocaleToggle } from "./locale-toggle";
import { ThemeToggle } from "./theme-toggle";

export function AppHeader({ user }: { user: User }) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const router = useRouter();
  const logout = useLogout();
  const [open, setOpen] = useState(false);

  const links = [
    { href: "/meetings", label: t("meetings"), icon: Video },
    { href: "/tasks", label: t("tasks"), icon: ClipboardList },
    { href: "/participants", label: t("participants"), icon: UsersRound },
    ...(user.role === "admin" ? [{ href: "/admin/directions", label: t("directions"), icon: Compass }] : []),
  ];
  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  const nav = (mobile: boolean) =>
    links.map(({ href, label, icon: Icon }) => (
      <Link
        key={href}
        href={href}
        onClick={() => setOpen(false)}
        className={cn(
          "relative inline-flex items-center gap-2 text-sm font-medium transition-colors",
          mobile ? "rounded-lg px-3 py-2.5" : "rounded-full px-3.5 py-2",
          isActive(href)
            ? "bg-brand-soft text-accent-foreground"
            : "text-muted-foreground hover:bg-muted hover:text-foreground",
        )}
      >
        <Icon className="size-4" />
        {label}
      </Link>
    ));

  const onLogout = () =>
    logout.mutate(undefined, {
      onSettled: () => router.replace("/login"),
    });

  return (
    <header className="bg-card/85 sticky top-0 z-40 border-b backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-6 px-4 sm:px-6">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Menu">
              <Menu />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72 p-4">
            <SheetTitle className="mb-4">
              <Wordmark />
            </SheetTitle>
            <nav className="flex flex-col gap-1">{nav(true)}</nav>
            <div className="mt-6">
              <LocaleToggle />
            </div>
          </SheetContent>
        </Sheet>

        <Link href="/meetings" className="shrink-0">
          <Wordmark />
        </Link>
        <nav className="hidden items-center gap-1 lg:flex">{nav(false)}</nav>

        <div className="ml-auto flex items-center gap-1.5">
          <LocaleToggle className="hidden sm:inline-flex" />
          <ThemeToggle />
          <NotificationBell />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="ring-offset-background focus-visible:ring-ring ml-1 rounded-full ring-offset-2 focus-visible:ring-2">
                <ParticipantAvatar name={user.name} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="font-normal">
                <div className="font-medium">{user.name}</div>
                <div className="text-muted-foreground text-xs">{user.email}</div>
                <div className="text-primary mt-1 text-[10px] font-semibold tracking-wider uppercase">
                  {user.role === "admin" ? t("admin") : t("user")}
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onLogout}>
                <LogOut /> {t("logout")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
