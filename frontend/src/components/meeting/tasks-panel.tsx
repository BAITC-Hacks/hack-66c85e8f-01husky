"use client";

import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCreateTask } from "@/lib/api/queries/tasks";
import type { Direction, Participant, Task } from "@/lib/api/types";
import { TaskCard } from "./task-card";

export function TasksPanel({
  meetingId,
  tasks,
  participants,
  directions,
  readOnly,
  highlightedId,
  onQuote,
}: {
  meetingId: number;
  tasks: Task[];
  participants: Participant[];
  directions: Direction[];
  readOnly: boolean;
  highlightedId: number | null;
  onQuote: (task: Task) => void;
}) {
  const t = useTranslations("taskTable");
  const create = useCreateTask();
  const [text, setText] = useState("");

  const add = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim().length < 3) return;
    create.mutate(
      { meeting_id: meetingId, text: text.trim() },
      { onSuccess: () => setText(""), onError: (err) => toast.error(err.message) },
    );
  };

  return (
    <div className="grid gap-3">
      {tasks.length === 0 && <p className="text-muted-foreground py-6 text-center text-sm">{t("empty")}</p>}
      <ol className="grid gap-3">
        {tasks.map((task, i) => (
          <TaskCard
            key={task.id}
            task={task}
            index={i}
            participants={participants}
            directions={directions}
            readOnly={readOnly}
            highlighted={highlightedId === task.id}
            onQuote={() => onQuote(task)}
          />
        ))}
      </ol>
      {!readOnly && (
        <form onSubmit={add} className="flex gap-2 rounded-xl border border-dashed p-2">
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={t("newTask")}
            className="h-9 border-0 bg-transparent shadow-none focus-visible:ring-0"
          />
          <Button type="submit" variant="secondary" disabled={create.isPending || text.trim().length < 3}>
            <Plus /> {t("add")}
          </Button>
        </form>
      )}
    </div>
  );
}
