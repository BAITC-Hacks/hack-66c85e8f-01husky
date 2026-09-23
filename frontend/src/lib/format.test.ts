import { describe, expect, it } from "vitest";
import {
  allowedStatuses,
  deadlineBucket,
  deadlineInfo,
  formatBytes,
  formatDuration,
  formatTimecode,
  initials,
  speakerColor,
  speakerIndex,
} from "./format";

describe("formatTimecode", () => {
  it("formats minutes and hours", () => {
    expect(formatTimecode(0)).toBe("00:00");
    expect(formatTimecode(74.9)).toBe("01:14");
    expect(formatTimecode(3725)).toBe("1:02:05");
  });
  it("clamps negatives", () => expect(formatTimecode(-3)).toBe("00:00"));
});

describe("formatDuration", () => {
  it("handles empty and short values", () => {
    expect(formatDuration(null)).toBe("—");
    expect(formatDuration(42)).toBe("00:42");
  });
  it("rounds to minutes and hours", () => {
    expect(formatDuration(184)).toBe("3 мин");
    expect(formatDuration(2710)).toBe("45 мин");
    expect(formatDuration(4000)).toBe("1 ч 7 мин");
  });
});

describe("deadlineInfo", () => {
  const today = "2026-09-23";
  it("no deadline", () =>
    expect(deadlineInfo(null, "confirmed", today)).toEqual({ days: null, tone: "none" }));
  it("overdue by date", () =>
    expect(deadlineInfo("2026-09-21", "in_progress", today)).toEqual({ days: -2, tone: "overdue" }));
  it("overdue by status", () => expect(deadlineInfo("2026-09-30", "overdue", today).tone).toBe("overdue"));
  it("soon within 2 days", () =>
    expect(deadlineInfo("2026-09-24", "confirmed", today)).toEqual({ days: 1, tone: "soon" }));
  it("ok later", () => expect(deadlineInfo("2026-10-10", "confirmed", today).tone).toBe("ok"));
  it("done wins", () => expect(deadlineInfo("2026-09-01", "done", today).tone).toBe("done"));
});

describe("speakers", () => {
  it("parses index", () => {
    expect(speakerIndex("SPEAKER_00")).toBe(0);
    expect(speakerIndex("SPEAKER_11")).toBe(11);
  });
  it("wraps palette", () => expect(speakerColor("SPEAKER_07")).toBe("var(--speaker-1)"));
});

describe("misc", () => {
  it("initials", () => expect(initials("Айбек Нуров")).toBe("АН"));
  it("bytes", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});

describe("task status transitions", () => {
  it("locks drafts", () => expect(allowedStatuses("draft")).toEqual(["draft"]));
  it("overdue can only move forward", () =>
    expect(allowedStatuses("overdue")).toEqual(["overdue", "in_progress", "done"]));
  it("done can be reopened", () => expect(allowedStatuses("done")).toContain("confirmed"));
});

describe("deadlineBucket", () => {
  const today = "2026-09-23";
  it("puts done last regardless of date", () =>
    expect(deadlineBucket("2026-01-01", "done", today)).toBe("done"));
  it("overdue by date or status", () => {
    expect(deadlineBucket("2026-09-22", "in_progress", today)).toBe("overdue");
    expect(deadlineBucket("2026-10-30", "overdue", today)).toBe("overdue");
  });
  it("splits upcoming", () => {
    expect(deadlineBucket("2026-09-23", "confirmed", today)).toBe("today");
    expect(deadlineBucket("2026-09-24", "confirmed", today)).toBe("tomorrow");
    expect(deadlineBucket("2026-09-30", "confirmed", today)).toBe("week");
    expect(deadlineBucket("2026-10-01", "confirmed", today)).toBe("later");
    expect(deadlineBucket(null, "confirmed", today)).toBe("none");
  });
});
