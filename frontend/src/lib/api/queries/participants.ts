"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type { Participant, ParticipantCreate } from "../types";
import { qk } from "./keys";

export function useParticipants() {
  return useQuery({
    queryKey: qk.participants,
    queryFn: () => api.get<Participant[]>("/participants"),
    staleTime: 30_000,
  });
}

export function useCreateParticipant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ParticipantCreate) => api.post<Participant>("/participants", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.participants }),
  });
}

export function useUpdateParticipant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<ParticipantCreate> & { id: number }) =>
      api.patch<Participant>(`/participants/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.participants }),
  });
}

export function useEnrollVoiceprint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, audio }: { id: number; audio: Blob }) => {
      const form = new FormData();
      form.append("file", audio, "voiceprint.webm");
      return api.postForm<{ ok: boolean; embedding_dim: number }>(`/participants/${id}/voiceprint`, form);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.participants }),
  });
}

export function useDeleteVoiceprint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.del<void>(`/participants/${id}/voiceprint`),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.participants }),
  });
}
