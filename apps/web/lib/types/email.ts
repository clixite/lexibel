export interface EmailThread {
  id: string;
  subject: string;
  participant_emails: string[];
  participant_names: string[];
  message_count: number;
  has_attachments: boolean;
  first_message_date: string;
  last_message_date: string;
  labels: string[];
  is_important: boolean;
  case_id?: string;
  case_title?: string;
}

export interface EmailMessage {
  id: string;
  thread_id: string;
  subject: string;
  from_email: string;
  from_name: string;
  to_emails: string[];
  cc_emails: string[];
  bcc_emails: string[];
  body_text: string;
  body_html: string;
  sent_at: string;
  received_at: string;
  has_attachments: boolean;
  attachment_count: number;
  attachments: EmailAttachment[];
  labels: string[];
  is_read: boolean;
  is_important: boolean;
  is_draft: boolean;
  in_reply_to?: string;
  references: string[];
  case_id?: string;
}

export interface EmailAttachment {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  download_url: string;
}

export interface EmailSyncStatus {
  provider: "google" | "microsoft";
  email_address: string;
  last_sync_at: string;
  total_messages: number;
  total_threads: number;
  sync_status: "syncing" | "completed" | "error";
  error_message?: string;
}

export interface EmailListFilters {
  page?: number;
  per_page?: number;
  thread_id?: string;
  case_id?: string;
  has_attachments?: boolean;
  is_important?: boolean;
  from_email?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
}

export interface EmailListResponse {
  items: EmailMessage[];
  total: number;
  page: number;
  per_page: number;
}

export interface EmailThreadListResponse {
  items: EmailThread[];
  total: number;
  page: number;
  per_page: number;
}

export interface EmailStats {
  total_messages: number;
  total_threads: number;
  unread_count: number;
  important_count: number;
  with_attachments: number;
  last_7_days: number;
  last_30_days: number;
}
