"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type {
  Locale,
  Meeting,
  MeetingBotCreate,
  MeetingDetail,
  MeetingFilters,
  MeetingListItem,
  MeetingLiveCreate,
  MeetingPatch,
  SpeakerAssign,
} from "../types";
import { qk } from "./keys";

const PROCESSING = new Set(["uploaded", "processing"]);

export function useMeetings(filters?: MeetingFilters) {
  return useQuery({
    queryKey: qk.meetings(filters),
    queryFn: () => api.get<MeetingListItem[]>("/meetings", { ...filters }),
    refetchInterval: (q) => (q.state.data?.some((m) => PROCESSING.has(m.status)) ? 5_000 : false),
  });
}

/** Polls every 3 s while the pipeline runs (spec §8.4). */
export function useMeeting(id: number) {
  return useQuery({
    queryKey: qk.meeting(id),
    queryFn: () => api.get<MeetingDetail>(`/meetings/${id}`),
    refetchInterval: (q) => (q.state.data && PROCESSING.has(q.state.data.meeting.status) ? 3_000 : false),
  });
}

function useInvalidateMeeting() {
  const qc = useQueryClient();
  return (id?: number) => {
    if (id) qc.invalidateQueries({ queryKey: qk.meeting(id) });
    qc.invalidateQueries({ queryKey: qk.meetingsAll });
    qc.invalidateQueries({ queryKey: qk.tasksAll });
    qc.invalidateQueries({ queryKey: qk.taskStats });
    qc.invalidateQueries({ queryKey: qk.notifications });
  };
}

export function useUploadMeeting() {
  const inv = useInvalidateMeeting();
  return useMutation({
    mutationFn: (v: {
      title: string;
      meeting_date: string;
      output_language: Locale;
      participant_ids: number[];
      file: File;
    }) => {
      const form = new FormData();
      form.append("title", v.title);
      form.append("meeting_date", v.meeting_date);
      form.append("output_language", v.output_language);
      v.participant_ids.forEach((id) => form.append("participant_ids", String(id)));
      form.append("file", v.file);
      return api.postForm<Meeting>("/meetings", form);
    },
    onSuccess: () => inv(),
  });
}

export function useCreateLiveMeeting() {
  return useMutation({
    mutationFn: (body: MeetingLiveCreate) => api.post<Meeting>("/meetings/live", body),
  });
}

export function useCreateBotMeeting() {
  const inv = useInvalidateMeeting();
  return useMutation({
    mutationFn: (body: MeetingBotCreate) => api.post<Meeting>("/meetings/bot", body),
    onSuccess: () => inv(),
  });
}

export function usePatchMeeting(id: number) {
  const inv = useInvalidateMeeting();
  return useMutation({
    mutationFn: (body: MeetingPatch) => api.patch<Meeting>(`/meetings/${id}`, body),
    onSuccess: () => inv(id),
  });
}

export function useAssignSpeakers(id: number) {
  const inv = useInvalidateMeeting();
  return useMutation({
    mutationFn: (body: SpeakerAssign[]) => api.put<MeetingDetail>(`/meetings/${id}/speakers`, body),
    onSuccess: () => inv(id),
  });
}

export function useMeetingAction(id: number, action: "reprocess" | "confirm") {
  const inv = useInvalidateMeeting();
  return useMutation({
    mutationFn: () => api.post<Meeting>(`/meetings/${id}/${action}`),
    onSuccess: () => inv(id),
  });
}

export function useSendToSed(id: number) {
  const inv = useInvalidateMeeting();
  return useMutation({
    mutationFn: () => api.post<{ sed_ref: string; outbox_path: string }>(`/meetings/${id}/sed`),
    onSuccess: () => inv(id),
  });
}

export function useDeleteAudio(id: number) {
  const inv = useInvalidateMeeting();
  return useMutation({
    mutationFn: () => api.del<void>(`/meetings/${id}/audio`),
    onSuccess: () => inv(id),
  });
}

export function useDeleteMeeting() {
  const inv = useInvalidateMeeting();
  return useMutation({
    mutationFn: (id: number) => api.del<void>(`/meetings/${id}`),
    onSuccess: () => inv(),
  });
}
