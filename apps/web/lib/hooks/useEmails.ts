import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  EmailMessage,
  EmailThread,
  EmailListResponse,
  EmailThreadListResponse,
  EmailListFilters,
  EmailStats,
  EmailSyncStatus,
} from "@/lib/types/email";

/**
 * Hook to fetch email threads
 */
export function useEmailThreads(
  filters: EmailListFilters,
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["email-threads", filters, tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");

      const params = new URLSearchParams();
      if (filters.page) params.set("page", String(filters.page));
      if (filters.per_page) params.set("per_page", String(filters.per_page));
      if (filters.case_id) params.set("case_id", filters.case_id);
      if (filters.has_attachments !== undefined)
        params.set("has_attachments", String(filters.has_attachments));
      if (filters.is_important !== undefined)
        params.set("is_important", String(filters.is_important));
      if (filters.search) params.set("search", filters.search);
      if (filters.date_from) params.set("date_from", filters.date_from);
      if (filters.date_to) params.set("date_to", filters.date_to);

      const url = params.toString()
        ? `/emails/threads?${params.toString()}`
        : "/emails/threads";

      return apiFetch<EmailThreadListResponse>(url, token, { tenantId });
    },
    enabled: !!token,
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to fetch emails in a thread
 */
export function useThreadEmails(
  threadId: string | undefined,
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["thread-emails", threadId, tenantId],
    queryFn: async () => {
      if (!token || !threadId) throw new Error("Missing parameters");
      return apiFetch<EmailListResponse>(
        `/emails/threads/${threadId}/messages`,
        token,
        { tenantId }
      );
    },
    enabled: !!token && !!threadId,
    staleTime: 30 * 1000,
  });
}

/**
 * Hook to fetch single email
 */
export function useEmail(
  emailId: string | undefined,
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["email", emailId, tenantId],
    queryFn: async () => {
      if (!token || !emailId) throw new Error("Missing parameters");
      return apiFetch<EmailMessage>(`/emails/${emailId}`, token, { tenantId });
    },
    enabled: !!token && !!emailId,
  });
}

/**
 * Hook to fetch email statistics
 */
export function useEmailStats(
  caseId: string | undefined,
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["email-stats", caseId, tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      const params = caseId
        ? `?case_id=${caseId}`
        : "";
      return apiFetch<EmailStats>(`/emails/stats${params}`, token, {
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
export function useEmailSyncStatus(
  token: string | undefined,
  tenantId: string | undefined
) {
  return useQuery({
    queryKey: ["email-sync-status", tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      return apiFetch<{ syncs: EmailSyncStatus[] }>(
        "/emails/sync-status",
        token,
        { tenantId }
      );
    },
    enabled: !!token,
    refetchInterval: 10000, // Refetch every 10 seconds
  });
}

/**
 * Hook to trigger email sync
 */
export function useTriggerEmailSync(
  token: string | undefined,
  tenantId: string | undefined
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (integrationId: string) => {
      if (!token) throw new Error("No token");
      return apiFetch(`/emails/sync/${integrationId}`, token, {
        method: "POST",
        tenantId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-sync-status"] });
      queryClient.invalidateQueries({ queryKey: ["email-threads"] });
      queryClient.invalidateQueries({ queryKey: ["email-stats"] });
    },
  });
}

/**
 * Hook to link email to case
 */
export function useLinkEmailToCase(
  token: string | undefined,
  tenantId: string | undefined
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      emailId,
      caseId,
    }: {
      emailId: string;
      caseId: string;
    }) => {
      if (!token) throw new Error("No token");
      return apiFetch(`/emails/${emailId}/link-case`, token, {
        method: "POST",
        body: JSON.stringify({ case_id: caseId }),
        tenantId,
      });
    },
    onSuccess: (_, { emailId }) => {
      queryClient.invalidateQueries({ queryKey: ["email", emailId] });
      queryClient.invalidateQueries({ queryKey: ["email-threads"] });
    },
  });
}

/**
 * Hook to mark email as read/unread
 */
export function useMarkEmailRead(
  token: string | undefined,
  tenantId: string | undefined
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      emailId,
      isRead,
    }: {
      emailId: string;
      isRead: boolean;
    }) => {
      if (!token) throw new Error("No token");
      return apiFetch(`/emails/${emailId}/mark-read`, token, {
        method: "POST",
        body: JSON.stringify({ is_read: isRead }),
        tenantId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["email-threads"] });
      queryClient.invalidateQueries({ queryKey: ["email-stats"] });
    },
  });
}
