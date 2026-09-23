import { ApiError, buildUrl, send } from "./client";

/**
 * Download a backend file via fetch → Blob so it works with cookie auth and
 * with the in-process mocks (a plain <a href> navigation would bypass them).
 */
export async function downloadFile(path: string, query: Record<string, string>, fallbackName: string) {
  const res = await send(buildUrl(path, query), { credentials: "include" });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, detail);
  }
  const cd = res.headers.get("Content-Disposition") ?? "";
  const name = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd)?.[1] ?? fallbackName;
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = decodeURIComponent(name);
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5_000);
}
