"use client";

import { parseISO } from "date-fns";
import { kk, ru } from "date-fns/locale";
import { CalendarDays, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { formatDate, toISODate } from "@/lib/format";
import { cn } from "@/lib/utils";

export function DatePicker({
  value,
  onChange,
  id,
  clearable = false,
  placeholder,
  className,
  size = "default",
}: {
  value: string | null;
  onChange: (v: string | null) => void;
  id?: string;
  clearable?: boolean;
  placeholder?: string;
  className?: string;
  size?: "default" | "sm";
}) {
  const locale = useLocale();
  const t = useTranslations("taskTable");
  const [open, setOpen] = useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          variant="outline"
          className={cn(
            "justify-start gap-2 font-normal",
            size === "default" ? "h-10 w-full" : "h-8",
            !value && "text-muted-foreground",
            className,
          )}
        >
          <CalendarDays className="size-4 opacity-60" />
          <span className="tabular">
            {value ? formatDate(value, locale) : (placeholder ?? t("noDeadline"))}
          </span>
          {clearable && value && (
            <span
              role="button"
              tabIndex={-1}
              className="hover:bg-muted ml-auto rounded p-0.5"
              onClick={(e) => {
                e.stopPropagation();
                onChange(null);
              }}
            >
              <X className="size-3.5" />
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          locale={locale === "kk" ? kk : ru}
          weekStartsOn={1}
          selected={value ? parseISO(value) : undefined}
          defaultMonth={value ? parseISO(value) : undefined}
          onSelect={(d) => {
            onChange(d ? toISODate(d) : null);
            setOpen(false);
          }}
        />
      </PopoverContent>
    </Popover>
  );
}
