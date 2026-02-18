/**
 * useEventStream — Real-time Server-Sent Events hook
 *
 * 2026 Best Practices:
 * - Automatic reconnection with exponential backoff
 * - Event type filtering
 * - TypeScript-safe event handlers
 * - Cleanup on unmount
 * - Error handling and logging
 *
 * Usage:
 * ```tsx
 * const { events, isConnected } = useEventStream({
 *   onCallEvent: (data) => {
 *     toast.success(`Appel reçu de ${data.contact_name}`);
 *     refreshTimeline();
 *   },
 * });
 * ```
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from '@/lib/useAuth';

interface EventStreamOptions {
  onCallEvent?: (data: CallEventData) => void;
  onCallAiCompleted?: (data: CallAiData) => void;
  onCaseUpdated?: (data: any) => void;
  onInboxItem?: (data: any) => void;
  autoReconnect?: boolean;
  reconnectDelay?: number; // milliseconds
}

interface CallEventData {
  event_id: string;
  call_id: string;
  direction: 'inbound' | 'outbound';
  call_type: 'answered' | 'missed' | 'voicemail';
  phone_number: string;
  contact_id?: string;
  contact_name?: string;
  case_id?: string;
  duration_seconds: number;
  has_recording: boolean;
  timestamp: string;
}

interface CallAiData {
  event_id: string;
  has_transcript: boolean;
  has_summary: boolean;
  sentiment_score?: number;
  tasks_generated: boolean;
}

interface EventStreamState {
  isConnected: boolean;
  isReconnecting: boolean;
  events: any[];
  error: Error | null;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function useEventStream(options: EventStreamOptions = {}): EventStreamState {
  const {
    onCallEvent,
    onCallAiCompleted,
    onCaseUpdated,
    onInboxItem,
    autoReconnect = true,
    reconnectDelay = 1000,
  } = options;

  const { accessToken } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [events, setEvents] = useState<any[]>([]);
  const [error, setError] = useState<Error | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);

  const connect = useCallback(() => {
    if (!accessToken) {
      console.warn('EventStream: No access token available');
      return;
    }

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const url = `${API_BASE_URL}/api/v1/events/stream`;

      // EventSource doesn't support custom headers directly
      // We append the token as a query parameter (alternative: use fetch-event-source)
      const urlWithAuth = `${url}?token=${accessToken}`;

      const eventSource = new EventSource(urlWithAuth);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('EventStream: Connected');
        setIsConnected(true);
        setIsReconnecting(false);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      // Handle 'connected' event
      eventSource.addEventListener('connected', (e) => {
        const data = JSON.parse(e.data);
        console.log('EventStream: Connection confirmed', data);
      });

      // Handle 'call_event_created' event
      eventSource.addEventListener('call_event_created', (e) => {
        const data: CallEventData = JSON.parse(e.data);
        console.log('EventStream: Call event received', data);

        setEvents((prev) => [...prev, { type: 'call_event_created', data }]);

        if (onCallEvent) {
          onCallEvent(data);
        }
      });

      // Handle 'call_ai_completed' event
      eventSource.addEventListener('call_ai_completed', (e) => {
        const data: CallAiData = JSON.parse(e.data);
        console.log('EventStream: Call AI completed', data);

        setEvents((prev) => [...prev, { type: 'call_ai_completed', data }]);

        if (onCallAiCompleted) {
          onCallAiCompleted(data);
        }
      });

      // Handle 'case_updated' event
      eventSource.addEventListener('case_updated', (e) => {
        const data = JSON.parse(e.data);

        setEvents((prev) => [...prev, { type: 'case_updated', data }]);

        if (onCaseUpdated) {
          onCaseUpdated(data);
        }
      });

      // Handle 'new_inbox_item' event
      eventSource.addEventListener('new_inbox_item', (e) => {
        const data = JSON.parse(e.data);

        setEvents((prev) => [...prev, { type: 'new_inbox_item', data }]);

        if (onInboxItem) {
          onInboxItem(data);
        }
      });

      eventSource.onerror = (err) => {
        console.error('EventStream: Error', err);
        setIsConnected(false);
        setError(new Error('EventSource connection failed'));

        // Attempt reconnection with exponential backoff
        if (autoReconnect) {
          setIsReconnecting(true);

          const backoffDelay = Math.min(
            reconnectDelay * Math.pow(2, reconnectAttemptsRef.current),
            30000 // Max 30 seconds
          );

          console.log(
            `EventStream: Reconnecting in ${backoffDelay}ms (attempt ${reconnectAttemptsRef.current + 1})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connect();
          }, backoffDelay);
        }
      };
    } catch (err) {
      console.error('EventStream: Failed to create EventSource', err);
      setError(err as Error);
    }
  }, [accessToken, autoReconnect, reconnectDelay, onCallEvent, onCallAiCompleted, onCaseUpdated, onInboxItem]);

  useEffect(() => {
    if (accessToken) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [accessToken, connect]);

  return {
    isConnected,
    isReconnecting,
    events,
    error,
  };
}
