import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  LegalChatRequest,
  LegalChatResponse,
  LegalChatMessage,
} from "@/lib/types/legal";

interface UseLegalChatParams {
  token: string | undefined;
  tenantId: string | undefined;
  onSuccess?: (response: LegalChatResponse) => void;
}

export function useLegalChat({ token, tenantId, onSuccess }: UseLegalChatParams) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: LegalChatRequest) => {
      if (!token) throw new Error("No token");
      return apiFetch<LegalChatResponse>("/legal/chat", token, {
        method: "POST",
        body: JSON.stringify(request),
        tenantId,
      });
    },
    onSuccess: (data) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ["legal-chat", data.conversation_id] });
      onSuccess?.(data);
    },
  });
}
