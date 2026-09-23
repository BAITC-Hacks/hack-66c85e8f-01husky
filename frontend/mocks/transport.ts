/**
 * In-process mock transport: resolves requests against the MSW handlers with
 * `getResponse`, no Service Worker. Works in any browser, including plain-HTTP
 * LAN demos where Service Workers are unavailable.
 */
import { getResponse } from "msw";
import { handlers } from "./handlers";
import { db, save, startProcessing } from "./db";

export async function mockFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const request = new Request(new URL(url, window.location.origin), init);
  const res = await getResponse(handlers, request);
  return res ?? Response.json({ detail: `No mock for ${init.method ?? "GET"} ${url}` }, { status: 404 });
}

/**
 * Minimal stand-in for WS /meetings/{id}/live: counts binary chunks and on
 * {"event":"stop"} marks audio present and starts the simulated pipeline.
 */
export class MockLiveSocket {
  readyState: number = WebSocket.CONNECTING;
  binaryType: BinaryType = "blob";
  onopen: ((e: Event) => void) | null = null;
  onclose: ((e: CloseEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  private bytes = 0;

  constructor(private meetingId: number) {
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      this.onopen?.(new Event("open"));
    }, 150);
  }

  send(data: string | Blob | ArrayBuffer) {
    if (typeof data !== "string") {
      this.bytes += data instanceof Blob ? data.size : data.byteLength;
      return;
    }
    if (JSON.parse(data).event !== "stop") return;
    const m = db.meetings.find((x) => x.id === this.meetingId);
    if (m) {
      m.has_audio = true;
      m.duration_sec = Math.max(1, Math.round(this.bytes / 4000));
      startProcessing(m);
      save();
    }
    this.onmessage?.(new MessageEvent("message", { data: JSON.stringify({ event: "stopped", bytes: this.bytes }) }));
    this.close();
  }

  close() {
    this.readyState = WebSocket.CLOSED;
    setTimeout(() => this.onclose?.(new CloseEvent("close", { code: 1000 })), 50);
  }
}
