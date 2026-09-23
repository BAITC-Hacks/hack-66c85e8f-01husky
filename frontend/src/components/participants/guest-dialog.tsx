"use client";

import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { toast } from "sonner";
import { Field } from "@/components/common/field";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useCreateParticipant } from "@/lib/api/queries/participants";
import type { Participant } from "@/lib/api/types";

/** Create a participant (guest = no user account) by name/email/position. */
export function GuestDialog({
  trigger,
  title,
  onCreated,
}: {
  trigger: ReactNode;
  title?: string;
  onCreated?: (p: Participant) => void;
}) {
  const t = useTranslations("newMeeting.fields");
  const tc = useTranslations("common");
  const create = useCreateParticipant();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [position, setPosition] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (name.trim().length < 2) return;
    create.mutate(
      { name: name.trim(), email: email.trim() || null, position: position.trim() || null },
      {
        onSuccess: (p) => {
          onCreated?.(p);
          setOpen(false);
          setName("");
          setEmail("");
          setPosition("");
        },
        onError: (err) => toast.error(err.message),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={submit} className="grid gap-4">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl">{title ?? t("addGuest")}</DialogTitle>
          </DialogHeader>
          <Field label={t("guestName")} htmlFor="g-name">
            <Input id="g-name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </Field>
          <Field label={t("guestEmail")} htmlFor="g-email" hint={tc("optional")}>
            <Input id="g-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label={t("guestPosition")} htmlFor="g-pos" hint={tc("optional")}>
            <Input id="g-pos" value={position} onChange={(e) => setPosition(e.target.value)} />
          </Field>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              {tc("cancel")}
            </Button>
            <Button type="submit" disabled={create.isPending || name.trim().length < 2}>
              {tc("add")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
