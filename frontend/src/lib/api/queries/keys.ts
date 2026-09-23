import type { MeetingFilters, TaskFilters } from "../types";

export const qk = {
  me: ["me"] as const,
  participants: ["participants"] as const,
  directions: ["directions"] as const,
  meetings: (f?: MeetingFilters) => ["meetings", f ?? {}] as const,
  meetingsAll: ["meetings"] as const,
  meeting: (id: number) => ["meeting", id] as const,
  tasks: (f?: TaskFilters) => ["tasks", f ?? {}] as const,
  tasksAll: ["tasks"] as const,
  taskStats: ["tasks-stats"] as const,
  notifications: ["notifications"] as const,
};
