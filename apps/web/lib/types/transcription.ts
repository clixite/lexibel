/**
 * TypeScript types for Transcription system
 * Mirrors backend Pydantic schemas for audio transcription
 */

export interface TranscriptionSegment {
  start: number;
  end: number;
  text: string;
  speaker?: string;
  confidence: number;
}

export interface Transcription {
  id: string;
  case_id?: string;
  file_name: string;
  file_size: number;
  duration_seconds: number;
  language: string;
  status: "pending" | "processing" | "completed" | "failed";
  full_text: string;
  segments: TranscriptionSegment[];
  speakers_detected: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface TranscriptionListResponse {
  items: Transcription[];
  total: number;
  page: number;
  per_page: number;
}

export interface UploadTranscriptionRequest {
  file: File;
  case_id?: string;
  language?: string;
  detect_speakers?: boolean;
}

export interface UploadTranscriptionResponse {
  id: string;
  status: string;
  message: string;
}

export interface SearchTranscriptionsParams {
  query?: string;
  case_id?: string;
  language?: string;
  status?: string;
  limit?: number;
  offset?: number;
}
