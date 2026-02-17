/**
 * Ringover API Client
 *
 * Type-safe API calls for Ringover integration
 */

import { apiClient } from './client';

export interface CallEvent {
  id: string;
  case_id?: string;
  contact_id?: string;
  contact_name?: string;
  direction: 'inbound' | 'outbound';
  call_type: 'answered' | 'missed' | 'voicemail';
  duration_formatted: string;
  phone_number: string;
  occurred_at: string;
  has_recording: boolean;
  has_transcript: boolean;
  has_summary: boolean;
  sentiment?: 'positive' | 'neutral' | 'negative';
  recording_url?: string;
  transcript?: string;
  ai_summary?: string;
  tasks_count: number;
}

export interface CallListResponse {
  items: CallEvent[];
  total: number;
  page: number;
  per_page: number;
}

export interface CallStats {
  total_calls: number;
  answered_calls: number;
  missed_calls: number;
  voicemails: number;
  total_duration_minutes: number;
  avg_duration_minutes: number;
  avg_sentiment_score?: number;
  calls_with_recordings: number;
  calls_with_transcripts: number;
}

export interface CallListFilters {
  page?: number;
  per_page?: number;
  direction?: 'inbound' | 'outbound';
  call_type?: 'answered' | 'missed' | 'voicemail';
  contact_id?: string;
  case_id?: string;
  date_from?: string;
  date_to?: string;
}

export const ringoverApi = {
  /**
   * List call history with filters
   */
  async listCalls(filters?: CallListFilters): Promise<CallListResponse> {
    const params = new URLSearchParams();

    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value));
        }
      });
    }

    const response = await apiClient.get(`/api/v1/ringover/calls?${params.toString()}`);
    return response.json();
  },

  /**
   * Get detailed call information
   */
  async getCall(eventId: string): Promise<CallEvent> {
    const response = await apiClient.get(`/api/v1/ringover/calls/${eventId}`);
    return response.json();
  },

  /**
   * Get call statistics
   */
  async getStats(days: number = 30, caseId?: string): Promise<CallStats> {
    const params = new URLSearchParams({ days: String(days) });
    if (caseId) {
      params.append('case_id', caseId);
    }

    const response = await apiClient.get(`/api/v1/ringover/stats?${params.toString()}`);
    return response.json();
  },

  /**
   * Download call recording
   */
  async downloadRecording(recordingUrl: string): Promise<Blob> {
    const response = await fetch(recordingUrl);
    if (!response.ok) {
      throw new Error('Failed to download recording');
    }
    return response.blob();
  },
};
