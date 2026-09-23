"use client";

import { formatDistanceToNow, parseISO } from "date-fns";
import { kk, ru } from "date-fns/locale";
import { AlarmClock, Bell, CheckCheck, FileCheck2, UserRoundCheck, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useNotifications, useReadAllNotifications, useReadNotification } from "@/lib/api/queries/notifications";
import type { Notification, NotificationKind } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const ICON: Record<NotificationKind, typeof Bell> = {
  assigned: UserRoundCheck,
  due_soon: AlarmClock,
  overdue: TriangleAlert,
  protocol_ready: FileCheck2,
};
const TONE: Record<NotificationKind, string> = {
  assigned: "text-primary bg-primary/10",
  due_soon: "text-gold bg-gold-soft",
  overdue: "text-brick bg-brick/10",
  protocol_ready: "text-sage bg-sage/10",
};

function href(n: Notification) {
  if (n.meeting_id && (n.kind === "protocol_ready" || !n.task_id)) return `/meetings/${n.meeting_id}`;
  return "/tasks";
}

export function NotificationBell() {
  const t = useTranslations("notifications");
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  const { data = [] } = useNotifications();
  const read = useReadNotification();
  const readAll = useReadAllNotifications();
  const unread = data.filter((n) => !n.read_at).length;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label={t("title")}>
          <Bell className={cn("size-[18px]", unread && "origin-top animate-[wiggle_1s_ease-in-out_1]")} />
          {unread > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-brick px-1 font-mono text-[10px] font-semibold text-white">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[min(92vw,380px)] p-0">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <span className="font-heading font-semibold">{t("title")}</span>
          <Button variant="ghost" size="xs" disabled={!unread || readAll.isPending} onClick={() => readAll.mutate()}>
            <CheckCheck /> {t("readAll")}
          </Button>
        </div>
        {data.length === 0 ? (
          <p className="px-4 py-10 text-center text-sm text-muted-foreground">{t("empty")}</p>
        ) : (
          <ScrollArea className="max-h-[420px]">
            <ul className="divide-y">
              {data.map((n) => {
                const Icon = ICON[n.kind];
                return (
                  <li key={n.id}>
                    <Link
                      href={href(n)}
                      onClick={() => {
                        if (!n.read_at) read.mutate(n.id);
                        setOpen(false);
                      }}
                      className={cn("flex gap-3 px-4 py-3 transition-colors hover:bg-muted/60", !n.read_at && "bg-gold-soft/30")}
                    >
                      <span className={cn("mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full", TONE[n.kind])}>
                        <Icon className="size-3.5" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-baseline justify-between gap-2">
                          <span className="truncate text-sm font-medium">{n.title}</span>
                          {!n.read_at && <span className="size-1.5 shrink-0 rounded-full bg-primary" />}
                        </span>
                        <span className="line-clamp-2 text-xs text-muted-foreground">{n.body}</span>
                        <span className="mt-1 block font-mono text-[10px] text-muted-foreground/80 uppercase">
                          {t(`kind.${n.kind}`)} ·{" "}
                          {formatDistanceToNow(parseISO(n.created_at), { addSuffix: true, locale: locale === "kk" ? kk : ru })}
                        </span>
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </ScrollArea>
        )}
      </PopoverContent>
    </Popover>
  );
}
