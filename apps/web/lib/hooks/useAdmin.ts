/**
 * Admin hooks for system health, stats, and integrations
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface ServiceHealth {
  status: "healthy" | "degraded" | "down";
  version?: string;
  latency_ms?: number;
  error?: string;
}

export interface SystemHealthResponse {
  status: "healthy" | "degraded" | "down";
  services: {
    api: ServiceHealth;
    database: ServiceHealth;
    redis: ServiceHealth;
    qdrant: ServiceHealth;
    minio: ServiceHealth;
    vllm?: ServiceHealth;
    neo4j?: ServiceHealth;
  };
  checked_at: string;
}

export interface AdminStatsResponse {
  tenants: number;
  users: number;
  cases: number;
  contacts: number;
  invoices: number;
  documents: number;
  time_entries: number;
}

export interface Integration {
  name: string;
  enabled: boolean;
  status: string;
  last_sync_at?: string;
}

export interface IntegrationsResponse {
  integrations: Integration[];
}

/**
 * Hook to fetch system health
 */
export function useAdminHealth(
  token: string | undefined,
  tenantId: string | undefined,
  enabled = true
) {
  return useQuery({
    queryKey: ["admin-health", tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      return apiFetch<SystemHealthResponse>("/admin/health", token, {
        tenantId,
      });
    },
    enabled: enabled && !!token,
    refetchInterval: 30000, // Refetch every 30 seconds
    staleTime: 10000, // 10 seconds
  });
}

/**
 * Hook to fetch admin stats
 */
export function useAdminStats(
  token: string | undefined,
  tenantId: string | undefined,
  enabled = true
) {
  return useQuery({
    queryKey: ["admin-stats", tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      return apiFetch<AdminStatsResponse>("/admin/stats", token, {
        tenantId,
      });
    },
    enabled: enabled && !!token,
    staleTime: 60000, // 1 minute
  });
}

/**
 * Hook to fetch integrations status
 */
export function useIntegrations(
  token: string | undefined,
  tenantId: string | undefined,
  enabled = true
) {
  return useQuery({
    queryKey: ["integrations-status", tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      return apiFetch<IntegrationsResponse>("/integrations/status", token, {
        tenantId,
      });
    },
    enabled: enabled && !!token,
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Hook to connect Google integration
 */
export function useConnectGoogle(
  token: string | undefined,
  tenantId: string | undefined
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("No token");
      return apiFetch<{ auth_url: string; state: string }>(
        "/integrations/google/auth-url",
        token,
        {
          method: "GET",
          tenantId,
        }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations-status"] });
    },
  });
}

/**
 * Hook to connect Microsoft integration
 */
export function useConnectMicrosoft(
  token: string | undefined,
  tenantId: string | undefined
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("No token");
      return apiFetch<{ auth_url: string; state: string }>(
        "/integrations/microsoft/auth-url",
        token,
        {
          method: "GET",
          tenantId,
        }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations-status"] });
    },
  });
}

/**
 * Hook to disconnect integration
 */
export function useDisconnectIntegration(
  token: string | undefined,
  tenantId: string | undefined
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (provider: "google" | "microsoft") => {
      if (!token) throw new Error("No token");
      return apiFetch(`/integrations/${provider}/disconnect`, token, {
        method: "DELETE",
        tenantId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations-status"] });
    },
  });
}

/**
 * Hook to list tenants (super admin only)
 */
export function useTenants(
  token: string | undefined,
  enabled = true
) {
  return useQuery({
    queryKey: ["admin-tenants"],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      return apiFetch<{ tenants: any[] }>("/admin/tenants", token);
    },
    enabled: enabled && !!token,
  });
}

/**
 * Hook to list users
 */
export function useUsers(
  token: string | undefined,
  tenantId: string | undefined,
  enabled = true
) {
  return useQuery({
    queryKey: ["admin-users", tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      return apiFetch<{ users: any[] }>("/admin/users", token, { tenantId });
    },
    enabled: enabled && !!token,
  });
}
