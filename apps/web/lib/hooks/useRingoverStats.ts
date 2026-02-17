import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { CallStats } from "@/lib/api/ringover";

export function useRingoverStats(
  days: number,
  caseId: string | undefined,
  token: string | undefined,
  tenantId: string | undefined,
) {
  return useQuery({
    queryKey: ["ringover-stats", days, caseId, tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");

      const params = new URLSearchParams({ days: String(days) });
      if (caseId) params.set("case_id", caseId);

      return apiFetch<CallStats>(`/ringover/stats?${params.toString()}`, token, {
        tenantId,
      });
    },
    enabled: !!token,
    staleTime: 60 * 1000, // 1 minute
  });
}
