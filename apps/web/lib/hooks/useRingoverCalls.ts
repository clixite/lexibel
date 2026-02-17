import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { CallListResponse, CallListFilters } from "@/lib/api/ringover";

export function useRingoverCalls(
  filters: CallListFilters,
  token: string | undefined,
  tenantId: string | undefined,
) {
  return useQuery({
    queryKey: ["ringover-calls", filters, tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");

      const params = new URLSearchParams();
      if (filters.page !== undefined) params.set("page", String(filters.page));
      if (filters.per_page !== undefined) params.set("per_page", String(filters.per_page));
      if (filters.direction) params.set("direction", filters.direction);
      if (filters.call_type) params.set("call_type", filters.call_type);
      if (filters.contact_id) params.set("contact_id", filters.contact_id);
      if (filters.case_id) params.set("case_id", filters.case_id);
      if (filters.date_from) params.set("date_from", filters.date_from);
      if (filters.date_to) params.set("date_to", filters.date_to);

      const url = params.toString()
        ? `/ringover/calls?${params.toString()}`
        : "/ringover/calls";

      return apiFetch<CallListResponse>(url, token, { tenantId });
    },
    enabled: !!token,
    staleTime: 30 * 1000, // 30 seconds
  });
}
