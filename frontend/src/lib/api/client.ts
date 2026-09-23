/**
 * Thin fetch wrapper for the backend. All requests go to same-origin
 * `/api/v1/*`; next.config.ts rewrites them to BACKEND_URL so the httpOnly
 * `access_token` cookie just works. In mock mode the MSW handlers answer in-process.
 */

export const API_PREFIX = "/api/v1";

export const MOCKING = process.env.NEXT_PUBLIC_API_MOCKING === "1";

/** fetch, or the in-process MSW handlers in mock mode (tree-shaken otherwise). */
export async function transport(url: string, init: RequestInit): Promise<Response> {
  if (MOCKING) {
    const { mockFetch } = await import("@mocks/transport");
    return mockFetch(url, init);
  }
  return fetch(url, init);
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

type Query = Record<string, string | number | boolean | undefined | null>;

export function buildUrl(path: string, query?: Query): string {
  const qs = new URLSearchParams();
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined || v === null || v === "" || v === false) continue;
      qs.set(k, v === true ? "1" : String(v));
    }
  }
  const s = qs.toString();
  return `${API_PREFIX}${path}${s ? `?${s}` : ""}`;
}

async function request<T>(
  method: string,
  path: string,
  opts: { query?: Query; body?: unknown; form?: FormData } = {},
): Promise<T> {
  const init: RequestInit = { method, credentials: "include", headers: {} };
  if (opts.form) {
    init.body = opts.form;
  } else if (opts.body !== undefined) {
    init.body = JSON.stringify(opts.body);
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  const res = await transport(buildUrl(path, opts.query), init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") detail = data.detail;
      else if (Array.isArray(data?.detail)) detail = data.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>("GET", path, { query }),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, { body }),
  postForm: <T>(path: string, form: FormData) => request<T>("POST", path, { form }),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, { body }),
  del: <T>(path: string) => request<T>("DELETE", path),
};

/** Minimal WebSocket surface used by the live recorder. */
export type LiveSocket = Pick<WebSocket, "readyState" | "send" | "close" | "binaryType"> & {
  onopen: ((e: Event) => void) | null;
  onclose: ((e: CloseEvent) => void) | null;
  onerror: ((e: Event) => void) | null;
};

/** Opens WS /meetings/{id}/live (or its mock). */
export async function openLiveSocket(meetingId: number): Promise<LiveSocket> {
  if (MOCKING) {
    const { MockLiveSocket } = await import("@mocks/transport");
    return new MockLiveSocket(meetingId) as unknown as LiveSocket;
  }
  return new WebSocket(wsUrl(`/meetings/${meetingId}/live`));
}

/** WebSocket base. Next rewrites don't proxy WS, so it goes straight to the backend. */
export function wsUrl(path: string): string {
  const base =
    process.env.NEXT_PUBLIC_WS_URL ||
    (typeof window !== "undefined"
      ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`
      : "ws://localhost:8000");
  return `${base}${API_PREFIX}${path}`;
}
