import { refreshAccessToken, logout } from "@/lib/auth-core";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/** Structured API error with status and detail */
export class ApiFetchError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiFetchError";
    this.status = status;
    this.detail = detail;
  }
}

export async function apiFetch<T = unknown>(
  path: string,
  accessToken: string,
  init?: RequestInit & { tenantId?: string },
): Promise<T> {
  const { tenantId, ...restInit } = init || {};

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${accessToken}`,
    ...(tenantId ? { "X-Tenant-ID": tenantId } : {}),
    ...((restInit?.headers as Record<string, string>) || {}),
  };

  const res = await fetch(`${API_BASE}${path}`, {
    ...restInit,
    headers,
  });

  // Auto-refresh on 401, then retry once
  if (res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Retry with refreshed token — get fresh token from storage
      const { getAccessToken } = await import("@/lib/auth-core");
      const newToken = getAccessToken();
      if (newToken) {
        headers["Authorization"] = `Bearer ${newToken}`;
        const retryRes = await fetch(`${API_BASE}${path}`, {
          ...restInit,
          headers,
        });
        if (retryRes.ok) {
          return retryRes.json();
        }
      }
    }
    // Refresh failed — redirect to login
    logout();
    throw new ApiFetchError(401, "Session expirée. Veuillez vous reconnecter.");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // response body wasn't JSON — keep statusText
    }
    throw new ApiFetchError(res.status, detail);
  }

  return res.json();
}
