import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { NetworkStats } from "@/lib/graph/graph-utils";

/**
 * Hook to get network statistics for a case
 */
export function useNetworkStats(
  caseId: string | undefined,
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["network-stats", caseId, tenantId],
    queryFn: async () => {
      if (!token || !caseId) throw new Error("Missing parameters");
      return apiFetch<NetworkStats>(`/graph/case/${caseId}/stats`, token, {
        tenantId,
      });
    },
    enabled: !!token && !!caseId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to compute client-side network stats from elements
 */
export function useClientNetworkStats(elements: any[]): NetworkStats | null {
  if (!elements || elements.length === 0) return null;

  const nodes = elements.filter((el) => !el.data.source && !el.data.target);
  const edges = elements.filter((el) => el.data.source && el.data.target);

  const totalNodes = nodes.length;
  const totalEdges = edges.length;

  // Calculate degree for each node
  const degrees = new Map<string, number>();
  nodes.forEach((node) => degrees.set(node.data.id, 0));

  edges.forEach((edge) => {
    degrees.set(edge.data.source, (degrees.get(edge.data.source) || 0) + 1);
    degrees.set(edge.data.target, (degrees.get(edge.data.target) || 0) + 1);
  });

  const degreeValues = Array.from(degrees.values());
  const avgDegree =
    totalNodes > 0
      ? degreeValues.reduce((sum, d) => sum + d, 0) / totalNodes
      : 0;
  const maxDegree = totalNodes > 0 ? Math.max(...degreeValues) : 0;

  // Network density
  const maxPossibleEdges = (totalNodes * (totalNodes - 1)) / 2;
  const density = maxPossibleEdges > 0 ? totalEdges / maxPossibleEdges : 0;

  // Connected components (simplified)
  const visited = new Set<string>();
  let connectedComponents = 0;

  const dfs = (nodeId: string) => {
    visited.add(nodeId);
    edges.forEach((edge) => {
      if (edge.data.source === nodeId && !visited.has(edge.data.target)) {
        dfs(edge.data.target);
      } else if (
        edge.data.target === nodeId &&
        !visited.has(edge.data.source)
      ) {
        dfs(edge.data.source);
      }
    });
  };

  nodes.forEach((node) => {
    if (!visited.has(node.data.id)) {
      connectedComponents++;
      dfs(node.data.id);
    }
  });

  return {
    total_nodes: totalNodes,
    total_edges: totalEdges,
    density,
    avg_degree: avgDegree,
    max_degree: maxDegree,
    connected_components: connectedComponents,
    diameter: 0, // Complex calculation, would need BFS
    avg_clustering: 0, // Complex calculation
  };
}
