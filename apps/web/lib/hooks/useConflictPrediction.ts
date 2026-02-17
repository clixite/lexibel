import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { ConflictPrediction } from "@/lib/graph/graph-utils";

export interface ConflictPredictionResponse {
  predictions: ConflictPrediction[];
  model_version: string;
  confidence_threshold: number;
}

/**
 * Hook to predict potential conflicts in a case
 */
export function useConflictPrediction(
  caseId: string | undefined,
  token: string | undefined,
  tenantId: string | undefined,
  minProbability = 0.5
) {
  return useQuery({
    queryKey: ["conflict-predictions", caseId, minProbability, tenantId],
    queryFn: async () => {
      if (!token || !caseId) throw new Error("Missing parameters");
      const params = new URLSearchParams({
        min_probability: String(minProbability),
      });
      return apiFetch<ConflictPredictionResponse>(
        `/graph/case/${caseId}/conflict-predictions?${params.toString()}`,
        token,
        { tenantId }
      );
    },
    enabled: !!token && !!caseId,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to predict conflicts between two specific entities
 */
export function usePairConflictPrediction(
  entityId1: string | undefined,
  entityId2: string | undefined,
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["pair-conflict-prediction", entityId1, entityId2, tenantId],
    queryFn: async () => {
      if (!token || !entityId1 || !entityId2)
        throw new Error("Missing parameters");
      return apiFetch<ConflictPrediction>(
        `/graph/predict-conflict/${entityId1}/${entityId2}`,
        token,
        { tenantId }
      );
    },
    enabled: !!token && !!entityId1 && !!entityId2,
    staleTime: 10 * 60 * 1000,
  });
}
