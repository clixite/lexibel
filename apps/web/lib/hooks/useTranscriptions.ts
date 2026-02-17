import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  TranscriptionListResponse,
  SearchTranscriptionsParams,
} from "@/lib/types/transcription";

export function useTranscriptions(
  params: SearchTranscriptionsParams,
  token: string | undefined,
  tenantId: string | undefined,
) {
  return useQuery({
    queryKey: ["transcriptions", params, tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");

      const searchParams = new URLSearchParams();
      if (params.query) searchParams.set("query", params.query);
      if (params.case_id) searchParams.set("case_id", params.case_id);
      if (params.language) searchParams.set("language", params.language);
      if (params.status) searchParams.set("status", params.status);
      if (params.limit !== undefined) searchParams.set("limit", String(params.limit));
      if (params.offset !== undefined) searchParams.set("offset", String(params.offset));

      const url = searchParams.toString()
        ? `/transcriptions?${searchParams.toString()}`
        : "/transcriptions";

      return apiFetch<TranscriptionListResponse>(url, token, { tenantId });
    },
    enabled: !!token,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}
