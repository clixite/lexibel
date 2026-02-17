/**
 * AI Hub hooks for document generation, summarization, and analysis
 */

import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface AIGenerateRequest {
  case_id?: string;
  template?: string;
  context?: string;
  prompt: string;
}

export interface AIGenerateResponse {
  content: string;
  citations: Array<{
    text: string;
    source: string;
    confidence: number;
  }>;
  metadata: Record<string, any>;
}

export interface AISummarizeRequest {
  case_id?: string;
  content?: string;
  max_length?: number;
}

export interface AIAnalyzeRequest {
  document_id?: string;
  content?: string;
  analysis_type?: "parties" | "obligations" | "risks" | "deadlines";
}

/**
 * Hook to generate document drafts with AI
 */
export function useAIDraft(
  token: string | undefined,
  tenantId: string | undefined
) {
  return useMutation({
    mutationFn: async (data: AIGenerateRequest) => {
      if (!token) throw new Error("No token");
      return apiFetch<AIGenerateResponse>("/ai/draft", token, {
        method: "POST",
        body: JSON.stringify(data),
        tenantId,
      });
    },
  });
}

/**
 * Hook to summarize cases or documents with AI
 */
export function useAISummarize(
  token: string | undefined,
  tenantId: string | undefined
) {
  return useMutation({
    mutationFn: async (data: AISummarizeRequest) => {
      if (!token) throw new Error("No token");
      return apiFetch<AIGenerateResponse>("/ai/summarize", token, {
        method: "POST",
        body: JSON.stringify(data),
        tenantId,
      });
    },
  });
}

/**
 * Hook to analyze documents with AI
 */
export function useAIAnalyze(
  token: string | undefined,
  tenantId: string | undefined
) {
  return useMutation({
    mutationFn: async (data: AIAnalyzeRequest) => {
      if (!token) throw new Error("No token");
      return apiFetch<AIGenerateResponse>("/ai/analyze", token, {
        method: "POST",
        body: JSON.stringify(data),
        tenantId,
      });
    },
  });
}

/**
 * Hook to transcribe audio with AI
 */
export function useAITranscribe(
  token: string | undefined,
  tenantId: string | undefined
) {
  return useMutation({
    mutationFn: async (formData: FormData) => {
      if (!token) throw new Error("No token");

      // Use fetch directly for multipart/form-data
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/ai/transcribe`,
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
        throw new Error(`Transcription failed: ${response.statusText}`);
      }

      return response.json();
    },
  });
}
