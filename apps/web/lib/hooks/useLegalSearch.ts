import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  LegalSearchParams,
  LegalSearchResponse,
} from "@/lib/types/legal";

export function useLegalSearch(
  params: LegalSearchParams,
  token: string | undefined,
  tenantId: string | undefined,
  enabled = true,
) {
  return useQuery({
    queryKey: ["legal-search", params, tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      const searchParams = new URLSearchParams();
      searchParams.set("q", params.q);
      if (params.jurisdiction) searchParams.set("jurisdiction", params.jurisdiction);
      if (params.document_type) searchParams.set("document_type", params.document_type);
      if (params.limit !== undefined) searchParams.set("limit", String(params.limit));
      if (params.enable_reranking !== undefined)
        searchParams.set("enable_reranking", String(params.enable_reranking));
      if (params.enable_multilingual !== undefined)
        searchParams.set("enable_multilingual", String(params.enable_multilingual));

      return apiFetch<LegalSearchResponse>(
        `/legal/search?${searchParams.toString()}`,
        token,
        { tenantId },
      );
    },
    enabled: enabled && !!token && !!params.q && params.q.length >= 3,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
