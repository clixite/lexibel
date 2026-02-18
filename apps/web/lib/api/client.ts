/**
 * API Client — Base HTTP client with auth and error handling
 */

import { getAccessToken } from "@/lib/auth-core";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getHeaders(): HeadersInit {
    const token = getAccessToken();
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    return headers;
  }

  async get(path: string): Promise<Response> {
    const headers = this.getHeaders();
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "GET",
      headers,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response;
  }

  async post(path: string, data?: any): Promise<Response> {
    const headers = this.getHeaders();
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers,
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response;
  }

  async put(path: string, data?: any): Promise<Response> {
    const headers = this.getHeaders();
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "PUT",
      headers,
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response;
  }

  async delete(path: string): Promise<Response> {
    const headers = this.getHeaders();
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "DELETE",
      headers,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response;
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
