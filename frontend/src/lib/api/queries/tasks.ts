"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type { Task, TaskCreate, TaskFilters, TaskPatch, TaskStats } from "../types";
import { qk } from "./keys";

export function useTasks(filters?: TaskFilters) {
  return useQuery({
    queryKey: qk.tasks(filters),
    queryFn: () => api.get<Task[]>("/tasks", { ...filters }),
  });
}

export function useTaskStats() {
  return useQuery({
    queryKey: qk.taskStats,
    queryFn: () => api.get<TaskStats>("/tasks/stats"),
  });
}

function useInvalidateTasks() {
  const qc = useQueryClient();
  return (meetingId?: number) => {
    qc.invalidateQueries({ queryKey: qk.tasksAll });
    qc.invalidateQueries({ queryKey: qk.taskStats });
    if (meetingId) qc.invalidateQueries({ queryKey: qk.meeting(meetingId) });
  };
}

export function useCreateTask() {
  const inv = useInvalidateTasks();
  return useMutation({
    mutationFn: (body: TaskCreate) => api.post<Task>("/tasks", body),
    onSuccess: (t) => inv(t.meeting_id),
  });
}

export function useUpdateTask() {
  const inv = useInvalidateTasks();
  return useMutation({
    mutationFn: ({ id, ...body }: TaskPatch & { id: number }) => api.patch<Task>(`/tasks/${id}`, body),
    onSuccess: (t) => inv(t.meeting_id),
  });
}

export function useDeleteTask() {
  const inv = useInvalidateTasks();
  return useMutation({
    mutationFn: ({ id }: { id: number; meetingId: number }) => api.del<void>(`/tasks/${id}`),
    onSuccess: (_, v) => inv(v.meetingId),
  });
}
