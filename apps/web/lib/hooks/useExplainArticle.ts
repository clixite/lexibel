import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  ExplainArticleRequest,
  ExplainArticleResponse,
} from "@/lib/types/legal";

interface UseExplainArticleParams {
  token: string | undefined;
  tenantId: string | undefined;
  onSuccess?: (response: ExplainArticleResponse) => void;
}

export function useExplainArticle({
  token,
  tenantId,
  onSuccess,
}: UseExplainArticleParams) {
  return useMutation({
    mutationFn: async (request: ExplainArticleRequest) => {
      if (!token) throw new Error("No token");
      return apiFetch<ExplainArticleResponse>("/legal/explain", token, {
        method: "POST",
        body: JSON.stringify(request),
        tenantId,
      });
    },
    onSuccess,
  });
}
