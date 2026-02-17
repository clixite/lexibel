import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  CalendarEvent,
  Calendar,
  CalendarListResponse,
  CalendarListFilters,
  CalendarStats,
  CalendarSyncStatus,
} from "@/lib/types/calendar";

/**
 * Hook to fetch calendars
 */
export function useCalendars(
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["calendars", tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      return apiFetch<{ items: Calendar[] }>("/calendar/calendars", token, {
        tenantId,
      });
    },
    enabled: !!token,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch calendar events
 */
export function useCalendarEvents(
  filters: CalendarListFilters,
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["calendar-events", filters, tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");

      const params = new URLSearchParams();
      if (filters.page) params.set("page", String(filters.page));
      if (filters.per_page) params.set("per_page", String(filters.per_page));
      if (filters.calendar_id) params.set("calendar_id", filters.calendar_id);
      if (filters.case_id) params.set("case_id", filters.case_id);
      if (filters.start_date) params.set("start_date", filters.start_date);
      if (filters.end_date) params.set("end_date", filters.end_date);
      if (filters.status) params.set("status", filters.status);
      if (filters.search) params.set("search", filters.search);

      const url = params.toString()
        ? `/calendar/events?${params.toString()}`
        : "/calendar/events";

      return apiFetch<CalendarListResponse>(url, token, { tenantId });
    },
    enabled: !!token,
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to fetch single event
 */
export function useCalendarEvent(
  eventId: string | undefined,
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["calendar-event", eventId, tenantId],
    queryFn: async () => {
      if (!token || !eventId) throw new Error("Missing parameters");
      return apiFetch<CalendarEvent>(`/calendar/events/${eventId}`, token, {
        tenantId,
      });
    },
    enabled: !!token && !!eventId,
  });
}

/**
 * Hook to fetch calendar statistics
 */
export function useCalendarStats(
  caseId: string | undefined,
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["calendar-stats", caseId, tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      const params = caseId ? `?case_id=${caseId}` : "";
      return apiFetch<CalendarStats>(`/calendar/stats${params}`, token, {
        tenantId,
      });
    },
    enabled: !!token,
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to get sync status
 */
export function useCalendarSyncStatus(
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["calendar-sync-status", tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      return apiFetch<{ syncs: CalendarSyncStatus[] }>(
        "/calendar/sync-status",
        token,
        { tenantId }
      );
    },
    enabled: !!token,
    refetchInterval: 10000, // Refetch every 10 seconds
  });
}

/**
 * Hook to trigger calendar sync
 */
export function useTriggerCalendarSync(
  token: string | undefined,
  tenantId: string | undefined
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (integrationId: string) => {
      if (!token) throw new Error("No token");
      return apiFetch(`/calendar/sync/${integrationId}`, token, {
        method: "POST",
        tenantId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calendar-sync-status"] });
      queryClient.invalidateQueries({ queryKey: ["calendar-events"] });
      queryClient.invalidateQueries({ queryKey: ["calendar-stats"] });
    },
  });
}

/**
 * Hook to link event to case
 */
export function useLinkEventToCase(
  token: string | undefined,
  tenantId: string | undefined
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      eventId,
      caseId,
    }: {
      eventId: string;
      caseId: string;
    }) => {
      if (!token) throw new Error("No token");
      return apiFetch(`/calendar/events/${eventId}/link-case`, token, {
        method: "POST",
        body: JSON.stringify({ case_id: caseId }),
        tenantId,
      });
    },
    onSuccess: (_, { eventId }) => {
      queryClient.invalidateQueries({ queryKey: ["calendar-event", eventId] });
      queryClient.invalidateQueries({ queryKey: ["calendar-events"] });
    },
  });
}
