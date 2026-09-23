"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type { Direction } from "../types";
import { qk } from "./keys";

export function useDirections() {
  return useQuery({
    queryKey: qk.directions,
    queryFn: () => api.get<Direction[]>("/directions"),
    staleTime: 5 * 60_000,
  });
}

export function useCreateDirection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string }) => api.post<Direction>("/directions", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.directions }),
  });
}

export function useUpdateDirection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<Omit<Direction, "id">> & { id: number }) =>
      api.patch<Direction>(`/directions/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.directions }),
  });
}
