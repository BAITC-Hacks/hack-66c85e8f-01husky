"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../client";
import type { LoginBody, RegisterBody, User } from "../types";
import { qk } from "./keys";

export function useMe() {
  return useQuery({
    queryKey: qk.me,
    queryFn: () => api.get<User>("/auth/me"),
    retry: (count, err) => !(err instanceof ApiError && err.status === 401) && count < 2,
    staleTime: 60_000,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: LoginBody) => api.post<User>("/auth/login", body),
    // 401 here means wrong credentials, not an expired session: the form shows it inline.
    meta: { silent: true },
    onSuccess: (user) => qc.setQueryData(qk.me, user),
  });
}

export function useRegister() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RegisterBody) => api.post<User>("/auth/register", body),
    onSuccess: (user) => qc.setQueryData(qk.me, user),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<void>("/auth/logout"),
    onSuccess: () => qc.clear(),
  });
}
