import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { GraphData } from "@/lib/graph/graph-utils";

export interface GraphSearchParams {
  query: string;
  case_id?: string;
  depth?: number;
}

/**
 * Hook to fetch case graph data
 */
export function useGraphData(
  caseId: string | undefined,
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["graph-data", caseId, tenantId],
    queryFn: async () => {
      if (!token || !caseId) throw new Error("Missing parameters");
      return apiFetch<GraphData>(`/graph/case/${caseId}`, token, {
        tenantId,
      });
    },
    enabled: !!token && !!caseId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

/**
 * Hook to search graph
 */
export function useGraphSearch(
  token: string | undefined,
  tenantId: string | undefined
) {
  return useMutation({
    mutationFn: async (params: GraphSearchParams) => {
      if (!token) throw new Error("No token");
      return apiFetch<{ context: GraphData }>("/graph/search", token, {
        method: "POST",
        body: JSON.stringify(params),
        tenantId,
      });
    },
  });
}

/**
 * Hook to build/rebuild case graph
 */
export function useBuildGraph(
  token: string | undefined,
  tenantId: string | undefined
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      caseId,
      documentIds,
    }: {
      caseId: string;
      documentIds?: string[];
    }) => {
      if (!token) throw new Error("No token");
      return apiFetch(`/graph/build/${caseId}`, token, {
        method: "POST",
        body: JSON.stringify({ documents: documentIds || [] }),
        tenantId,
      });
    },
    onSuccess: (_, { caseId }) => {
      queryClient.invalidateQueries({
        queryKey: ["graph-data", caseId, tenantId],
      });
      queryClient.invalidateQueries({
        queryKey: ["conflicts", caseId, tenantId],
      });
      queryClient.invalidateQueries({
        queryKey: ["network-stats", caseId, tenantId],
      });
    },
  });
}

/**
 * Hook to expand node neighborhood
 */
export function useExpandNode(
  token: string | undefined,
  tenantId: string | undefined
) {
  return useMutation({
    mutationFn: async ({
      nodeId,
      depth,
    }: {
      nodeId: string;
      depth?: number;
    }) => {
      if (!token) throw new Error("No token");
      const params = new URLSearchParams({ depth: String(depth || 1) });
      return apiFetch<GraphData>(
        `/graph/expand/${nodeId}?${params.toString()}`,
        token,
        { tenantId }
      );
    },
  });
}
