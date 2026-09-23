"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type { Notification } from "../types";
import { qk } from "./keys";

/** Bell polling every 30 s (spec §8.8). */
export function useNotifications() {
  return useQuery({
    queryKey: qk.notifications,
    queryFn: () => api.get<Notification[]>("/notifications"),
    refetchInterval: 30_000,
  });
}

export function useReadNotification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.post<void>(`/notifications/${id}/read`),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.notifications }),
  });
}

export function useReadAllNotifications() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<void>("/notifications/read-all"),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.notifications }),
  });
}
