export interface CalendarEvent {
  id: string;
  calendar_id: string;
  title: string;
  description: string;
  location: string;
  start_time: string;
  end_time: string;
  is_all_day: boolean;
  attendees: CalendarAttendee[];
  organizer_email: string;
  organizer_name: string;
  status: "confirmed" | "tentative" | "cancelled";
  visibility: "public" | "private" | "confidential";
  recurrence_rule?: string;
  is_recurring: boolean;
  case_id?: string;
  case_title?: string;
  created_at: string;
  updated_at: string;
}

export interface CalendarAttendee {
  email: string;
  name: string;
  response_status: "accepted" | "declined" | "tentative" | "needsAction";
  is_organizer: boolean;
  is_optional: boolean;
}

export interface Calendar {
  id: string;
  provider: "google" | "microsoft";
  email_address: string;
  name: string;
  description: string;
  color: string;
  is_primary: boolean;
  timezone: string;
  created_at: string;
}

export interface CalendarListFilters {
  page?: number;
  per_page?: number;
  calendar_id?: string;
  case_id?: string;
  start_date?: string;
  end_date?: string;
  status?: "confirmed" | "tentative" | "cancelled";
  search?: string;
}

export interface CalendarListResponse {
  items: CalendarEvent[];
  total: number;
  page: number;
  per_page: number;
}

export interface CalendarStats {
  total_events: number;
  upcoming_events: number;
  today_events: number;
  this_week_events: number;
  this_month_events: number;
  linked_to_cases: number;
}

export interface CalendarSyncStatus {
  provider: "google" | "microsoft";
  email_address: string;
  calendar_count: number;
  last_sync_at: string;
  sync_status: "syncing" | "completed" | "error";
  error_message?: string;
}
