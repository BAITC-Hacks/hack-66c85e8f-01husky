"use client";

import { AudioWaveform, Check, ChevronsUpDown, UserPlus, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { ParticipantAvatar } from "@/components/common/bits";
import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useParticipants } from "@/lib/api/queries/participants";
import { cn } from "@/lib/utils";
import { GuestDialog } from "./guest-dialog";

/** Multi-select of participants + inline "add guest" (spec §8.3). */
export function ParticipantPicker({
  value,
  onChange,
  invalid,
}: {
  value: number[];
  onChange: (ids: number[]) => void;
  invalid?: boolean;
}) {
  const t = useTranslations("newMeeting.fields");
  const tc = useTranslations("common");
  const tp = useTranslations("participants");
  const { data: all = [] } = useParticipants();
  const [open, setOpen] = useState(false);
  const selected = all.filter((p) => value.includes(p.id));
  const toggle = (id: number) => onChange(value.includes(id) ? value.filter((x) => x !== id) : [...value, id]);

  return (
    <div className="grid gap-2">
      <div className="flex gap-2">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              role="combobox"
              aria-invalid={invalid}
              className="h-10 flex-1 justify-between font-normal text-muted-foreground"
            >
              {value.length ? `${t("participants")}: ${value.length}` : t("participantsPlaceholder")}
              <ChevronsUpDown className="size-4 opacity-50" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-(--radix-popover-trigger-width) min-w-72 p-0" align="start">
            <Command>
              <CommandInput placeholder={tc("search")} />
              <CommandList>
                <CommandEmpty>{tc("notFound")}</CommandEmpty>
                <CommandGroup>
                  {all.map((p) => (
                    <CommandItem key={p.id} value={`${p.name} ${p.position ?? ""} ${p.email ?? ""}`} onSelect={() => toggle(p.id)}>
                      <ParticipantAvatar name={p.name} size="sm" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate">{p.name}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {p.position ?? (p.user_id ? tp("account") : tp("guest"))}
                        </span>
                      </span>
                      {p.has_voiceprint && <AudioWaveform className="size-3.5 text-mint" aria-label={tp("hasVoiceprint")} />}
                      <Check className={cn("size-4", value.includes(p.id) ? "opacity-100" : "opacity-0")} />
                    </CommandItem>
                  ))}
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
        <GuestDialog
          onCreated={(p) => onChange([...value, p.id])}
          trigger={
            <Button type="button" variant="outline" className="h-10" title={t("addGuest")}>
              <UserPlus />
              <span className="hidden sm:inline">{t("addGuest")}</span>
            </Button>
          }
        />
      </div>
      {selected.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {selected.map((p) => (
            <li
              key={p.id}
              className="inline-flex items-center gap-1.5 rounded-full border bg-card py-0.5 pr-1 pl-0.5 text-sm"
            >
              <ParticipantAvatar name={p.name} size="sm" />
              {p.name}
              {p.has_voiceprint && <AudioWaveform className="size-3 text-mint" />}
              <button
                type="button"
                onClick={() => toggle(p.id)}
                className="rounded-full p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                aria-label={tc("delete")}
              >
                <X className="size-3" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
