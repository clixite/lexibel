/**
 * API Client — Base HTTP client with auth, error handling, retry logic,
 * and automatic token refresh on 401.
 */

import { getAccessToken, refreshAccessToken, logout } from "@/lib/auth-core";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Structured API error with status code and parsed detail */
export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** Parse error detail from API response body */
async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (body.detail) return JSON.stringify(body.detail);
    if (body.message) return body.message;
  } catch {
    // Not JSON
  }
  return response.statusText || "Unknown error";
}

class ApiClient {
  private baseUrl: string;
  private refreshPromise: Promise<boolean> | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getHeaders(contentType?: string): Record<string, string> {
    const token = getAccessToken();
    const headers: Record<string, string> = {};

    if (contentType) {
      headers["Content-Type"] = contentType;
    }

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    return headers;
  }

  /** Handle 401 by refreshing token once, then retry */
  private async handleUnauthorized(): Promise<boolean> {
    // Deduplicate concurrent refresh calls
    if (!this.refreshPromise) {
      this.refreshPromise = refreshAccessToken().finally(() => {
        this.refreshPromise = null;
      });
    }
    return this.refreshPromise;
  }

  private async request(
    method: string,
    path: string,
    body?: unknown,
    retry = true,
  ): Promise<Response> {
    const headers = this.getHeaders(
      body !== undefined ? "application/json" : undefined,
    );

    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    // Auto-refresh on 401
    if (response.status === 401 && retry) {
      const refreshed = await this.handleUnauthorized();
      if (refreshed) {
        return this.request(method, path, body, false);
      }
      logout();
      throw new ApiError(401, "Session expirée. Veuillez vous reconnecter.");
    }

    if (!response.ok) {
      const detail = await parseErrorDetail(response);
      throw new ApiError(response.status, detail);
    }

    return response;
  }

  async get<T = unknown>(path: string): Promise<T> {
    const response = await this.request("GET", path);
    return response.json();
  }

  async post<T = unknown>(path: string, data?: unknown): Promise<T> {
    const response = await this.request("POST", path, data);
    return response.json();
  }

  async put<T = unknown>(path: string, data?: unknown): Promise<T> {
    const response = await this.request("PUT", path, data);
    return response.json();
  }

  async patch<T = unknown>(path: string, data?: unknown): Promise<T> {
    const response = await this.request("PATCH", path, data);
    return response.json();
  }

  async delete<T = unknown>(path: string): Promise<T> {
    const response = await this.request("DELETE", path);
    return response.json();
  }

  /** Raw request for cases where you need the Response object directly */
  async raw(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<Response> {
    return this.request(method, path, body);
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
