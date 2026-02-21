"use client";

import { useEffect, useState, useRef } from "react";
import { ConflictDetail } from "@/lib/sentinel/api-client";

interface SentinelAlert {
  type: "conflict_detected" | "conflict_resolved";
  conflict?: ConflictDetail;
  message?: string;
  timestamp: string;
}

export function useSentinelAlerts() {
  const [alerts, setAlerts] = useState<SentinelAlert[]>([]);
  const [conflictCount, setConflictCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // SSE is only available in browser
    if (typeof window === "undefined" || typeof EventSource === "undefined") return;

    // Create SSE connection
    let eventSource: EventSource;
    try {
      eventSource = new EventSource("/api/sentinel/alerts/stream");
    } catch {
      // EventSource creation failed — skip SSE
      return;
    }
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.addEventListener("connected", () => {
      // Connection confirmed
    });

    eventSource.addEventListener("conflict_detected", (event) => {
      try {
        const data = JSON.parse(event.data);
        const alert: SentinelAlert = {
          type: "conflict_detected",
          conflict: data.conflict,
          message: data.message,
          timestamp: data.timestamp || new Date().toISOString(),
        };

        setAlerts((prev) => [alert, ...prev].slice(0, 50)); // Keep last 50
        setConflictCount((prev) => prev + 1);

        // Show browser notification if permission granted
        if (typeof Notification !== "undefined" && Notification.permission === "granted" && data.conflict) {
          new Notification("Nouveau conflit détecté", {
            body: `Conflit ${data.conflict.conflict_type} avec sévérité ${data.conflict.severity_score}`,
            icon: "/favicon.ico",
          });
        }
      } catch (error) {
        console.error("[SENTINEL SSE] Error parsing conflict_detected event:", error);
      }
    });

    eventSource.addEventListener("conflict_resolved", (event) => {
      try {
        const data = JSON.parse(event.data);
        const alert: SentinelAlert = {
          type: "conflict_resolved",
          message: data.message,
          timestamp: data.timestamp || new Date().toISOString(),
        };

        setAlerts((prev) => [alert, ...prev].slice(0, 50));
        setConflictCount((prev) => Math.max(0, prev - 1));
      } catch (error) {
        console.error("[SENTINEL SSE] Error parsing conflict_resolved event:", error);
      }
    });

    eventSource.addEventListener("heartbeat", () => {
      // Just keep connection alive
    });

    eventSource.onerror = (error) => {
      console.error("[SENTINEL SSE] Connection error:", error);
      setIsConnected(false);

      // Auto-reconnect after 5 seconds
      setTimeout(() => {
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
        }
        // Will reconnect on next render
      }, 5000);
    };

    // Request notification permission
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission();
    }

    // Cleanup
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return {
    alerts,
    conflictCount,
    isConnected,
  };
}
