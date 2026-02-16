const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function apiFetch<T = any>(
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

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Session expirée. Veuillez vous reconnecter.");
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
    throw new Error(`API ${res.status}: ${detail}`);
  }

  return res.json();
}
