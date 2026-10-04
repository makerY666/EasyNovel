export interface BackendConfig {
  base_url: string;
  token: string;
}
declare global {
  interface Window {
    __EASYNOVEL__?: BackendConfig;
    __TAURI_INTERNALS__?: unknown;
  }
}
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export class Api {
  constructor(public config: BackendConfig) {}
  private authorization() {
    // A same-document launch can change the hash before React handles hashchange.
    // Existing browser polling clients must use that session at request dispatch.
    if (
      !this.config.base_url &&
      !window.__EASYNOVEL__ &&
      !window.__TAURI_INTERNALS__
    ) {
      const token =
        new URLSearchParams(window.location.hash.slice(1)).get("session") ||
        sessionStorage.getItem("easynovel.token");
      if (token) this.config.token = token;
    }
    return `Bearer ${this.config.token}`;
  }
  url(path: string) {
    return `${this.config.base_url.replace(/\/$/, "")}/api/v1${path}`;
  }
  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers);
    headers.set("Authorization", this.authorization());
    if (options.body && !(options.body instanceof FormData))
      headers.set("Content-Type", "application/json");
    const response = await fetch(this.url(path), { ...options, headers });
    if (!response.ok) {
      let message = `请求失败 (${response.status})`;
      try {
        const body = await response.json();
        message =
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail ?? body);
      } catch {
        /* preserve HTTP error */
      }
      throw new ApiError(response.status, message);
    }
    return response.status === 204
      ? (undefined as T)
      : ((await response.json()) as T);
  }
  get<T>(path: string) {
    return this.request<T>(path);
  }
  post<T>(path: string, body: unknown = {}) {
    return this.request<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }
  patch<T>(path: string, body: unknown) {
    return this.request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }
  delete<T>(path: string) {
    return this.request<T>(path, { method: "DELETE" });
  }
  async download(path: string, fallback: string) {
    const response = await fetch(this.url(path), {
      headers: { Authorization: this.authorization() },
    });
    if (!response.ok) throw new ApiError(response.status, "下载失败");
    const url = URL.createObjectURL(await response.blob());
    const a = document.createElement("a");
    a.href = url;
    const disposition = response.headers.get("Content-Disposition");
    const encoded = disposition?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
    a.download = encoded ? decodeURIComponent(encoded) : fallback;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }
  async events(
    runId: string,
    after: number,
    signal: AbortSignal,
    onEvent: (value: { seq: number; event: string; data: unknown }) => void,
  ) {
    const response = await fetch(
      this.url(`/runs/${runId}/events?after=${after}`),
      { headers: { Authorization: this.authorization() }, signal },
    );
    if (!response.ok || !response.body) throw new Error("事件连接不可用");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (!signal.aborted) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
      let boundary: number;
      while ((boundary = buffer.indexOf("\n\n")) >= 0) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const lines = frame
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart());
        if (lines.length) {
          const item = JSON.parse(lines.join("\n"));
          onEvent(item);
        }
      }
    }
  }
}
export function bootstrapBrowser(): BackendConfig | null {
  const startupParams = new URLSearchParams(window.location.hash.slice(1));
  if (startupParams.has("session")) {
    const startupToken = startupParams.get("session");
    startupParams.delete("session");
    const remainingHash = startupParams.toString();
    history.replaceState(
      history.state,
      "",
      window.location.pathname +
        window.location.search +
        (remainingHash ? "#" + remainingHash : ""),
    );
    if (startupToken) sessionStorage.setItem("easynovel.token", startupToken);
  }
  if (window.__EASYNOVEL__) return window.__EASYNOVEL__;
  if (window.__TAURI_INTERNALS__) return null;
  const token = sessionStorage.getItem("easynovel.token");
  return token ? { base_url: "", token } : null;
}
export async function bootstrap(): Promise<BackendConfig | null> {
  const browserConfig = bootstrapBrowser();
  if (window.__TAURI_INTERNALS__) {
    if (browserConfig) return browserConfig;
    const { invoke } = await import("@tauri-apps/api/core");
    return invoke<BackendConfig>("backend_config");
  }
  return browserConfig;
}
