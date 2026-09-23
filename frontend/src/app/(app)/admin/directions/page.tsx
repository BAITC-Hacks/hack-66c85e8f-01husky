"use client";

import { Lock, Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { toast } from "sonner";
import { EmptyState, PageHeader } from "@/components/common/bits";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useMe } from "@/lib/api/queries/auth";
import { useCreateDirection, useDirections, useUpdateDirection } from "@/lib/api/queries/directions";
import { cn } from "@/lib/utils";

export default function DirectionsPage() {
  const t = useTranslations("directions");
  const { data: me } = useMe();
  const { data = [] } = useDirections();
  const create = useCreateDirection();
  const update = useUpdateDirection();
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<{ id: number; name: string } | null>(null);

  if (me && me.role !== "admin") {
    return (
      <EmptyState
        title={t("adminOnly")}
        action={<Lock className="size-5 text-muted-foreground" />}
      />
    );
  }

  const add = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    create.mutate({ name: name.trim() }, { onSuccess: () => setName(""), onError: (err) => toast.error(err.message) });
  };

  const rename = () => {
    if (!editing) return;
    const orig = data.find((d) => d.id === editing.id);
    if (editing.name.trim() && editing.name !== orig?.name) {
      update.mutate({ id: editing.id, name: editing.name.trim() }, { onError: (err) => toast.error(err.message) });
    }
    setEditing(null);
  };

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader eyebrow={t("subtitle")} title={t("title")} />

      <form onSubmit={add} className="mb-6 flex gap-2">
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("placeholder")} className="h-10" />
        <Button type="submit" size="lg" className="h-10" disabled={create.isPending || !name.trim()}>
          <Plus /> {t("add")}
        </Button>
      </form>

      <ol className="overflow-hidden rounded-xl border bg-card shadow-soft">
        {data.map((d, i) => (
          <li key={d.id} className="flex items-center gap-4 border-b px-4 py-3 last:border-b-0">
            <span className="w-6 font-mono text-[11px] text-muted-foreground tabular">{String(i + 1).padStart(2, "0")}</span>
            {editing?.id === d.id ? (
              <Input
                autoFocus
                value={editing.name}
                onChange={(e) => setEditing({ id: d.id, name: e.target.value })}
                onBlur={rename}
                onKeyDown={(e) => e.key === "Enter" && rename()}
                className="h-8 flex-1"
              />
            ) : (
              <button
                onClick={() => setEditing({ id: d.id, name: d.name })}
                className={cn("flex-1 text-left font-heading text-[15px]", !d.is_active && "text-muted-foreground line-through")}
              >
                {d.name}
              </button>
            )}
            <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
              {t("active")}
              <Switch
                checked={d.is_active}
                onCheckedChange={(v) => update.mutate({ id: d.id, is_active: v }, { onError: (err) => toast.error(err.message) })}
              />
            </label>
          </li>
        ))}
      </ol>
    </div>
  );
}
