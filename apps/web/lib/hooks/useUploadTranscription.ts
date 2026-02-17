import { useMutation, useQueryClient } from "@tanstack/react-query";
import type {
  UploadTranscriptionRequest,
  UploadTranscriptionResponse,
} from "@/lib/types/transcription";

interface UseUploadTranscriptionParams {
  token: string | undefined;
  tenantId: string | undefined;
  onSuccess?: (response: UploadTranscriptionResponse) => void;
  onError?: (error: Error) => void;
}

export function useUploadTranscription({
  token,
  tenantId,
  onSuccess,
  onError,
}: UseUploadTranscriptionParams) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: UploadTranscriptionRequest) => {
      if (!token) throw new Error("No token");

      const formData = new FormData();
      formData.append("file", request.file);
      if (request.case_id) formData.append("case_id", request.case_id);
      if (request.language) formData.append("language", request.language);
      if (request.detect_speakers !== undefined)
        formData.append("detect_speakers", String(request.detect_speakers));

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/transcriptions`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            ...(tenantId && { "X-Tenant-ID": tenantId }),
          },
          body: formData,
        }
      );

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "Upload failed");
      }

      return response.json() as Promise<UploadTranscriptionResponse>;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["transcriptions"] });
      onSuccess?.(data);
    },
    onError,
  });
}
