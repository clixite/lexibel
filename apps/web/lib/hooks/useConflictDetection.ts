import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { ConflictDetection } from "@/lib/graph/graph-utils";

export interface ConflictsResponse {
  conflicts: ConflictDetection[];
  total: number;
}

/**
 * Hook to detect conflicts in a case
 */
export function useConflictDetection(
  caseId: string | undefined,
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["conflicts", caseId, tenantId],
    queryFn: async () => {
      if (!token || !caseId) throw new Error("Missing parameters");
      return apiFetch<ConflictsResponse>(
        `/graph/case/${caseId}/conflicts`,
        token,
        { tenantId }
      );
    },
    enabled: !!token && !!caseId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to get conflicts for a specific entity
 */
export function useEntityConflicts(
  entityId: string | undefined,
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["entity-conflicts", entityId, tenantId],
    queryFn: async () => {
      if (!token || !entityId) throw new Error("Missing parameters");
      return apiFetch<ConflictsResponse>(
        `/graph/entity/${entityId}/conflicts`,
        token,
        { tenantId }
      );
    },
    enabled: !!token && !!entityId,
    staleTime: 5 * 60 * 1000,
  });
}
