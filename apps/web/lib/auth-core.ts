/**
 * Auth Core — JWT token management (localStorage-based)
 *
 * Replaces next-auth with a simple, reliable JWT auth system
 * that works directly with the LexiBel API backend.
 */

const TOKEN_KEY = "lexibel_access_token";
const REFRESH_KEY = "lexibel_refresh_token";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface AuthUser {
  id: string;
  email: string;
  role: string;
  tenantId: string;
  fullName?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  mfa_required?: boolean;
}

// ── Token Storage ──

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_KEY, refreshToken);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// ── JWT Decode (client-side only, no verification) ──

export function decodeUser(token: string): AuthUser | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    // Check expiry
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      return null;
    }
    return {
      id: payload.sub,
      email: payload.email,
      role: payload.role,
      tenantId: payload.tid,
      fullName: payload.full_name || payload.name || payload.email,
    };
  } catch {
    return null;
  }
}

export function getCurrentUser(): AuthUser | null {
  const token = getAccessToken();
  if (!token) return null;
  return decodeUser(token);
}

export function isTokenValid(): boolean {
  return getCurrentUser() !== null;
}

// ── API Calls ──

export async function loginApi(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Erreur de connexion" }));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "Identifiants incorrects",
    );
  }

  const data: LoginResponse = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) return false;

    const data = await res.json();
    setTokens(data.access_token, data.refresh_token || refreshToken);
    return true;
  } catch {
    return false;
  }
}

export function logout(): void {
  clearTokens();
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}
