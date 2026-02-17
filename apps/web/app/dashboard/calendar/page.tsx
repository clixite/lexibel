"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Calendar as CalendarIcon,
  Search,
  Clock,
  MapPin,
  Users,
  Loader2,
  AlertCircle,
  CheckCircle,
  XCircle,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import {
  useCalendarEvents,
  useCalendarStats,
  useCalendars,
} from "@/lib/hooks/useCalendar";
import type { CalendarListFilters } from "@/lib/types/calendar";

const STATUS_ICONS = {
  confirmed: CheckCircle,
  tentative: HelpCircle,
  cancelled: XCircle,
};

const STATUS_COLORS = {
  confirmed: "text-green-600 bg-green-50",
  tentative: "text-yellow-600 bg-yellow-50",
  cancelled: "text-red-600 bg-red-50",
};

const STATUS_LABELS = {
  confirmed: "Confirmé",
  tentative: "Provisoire",
  cancelled: "Annulé",
};

export default function CalendarPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const user = session?.user as any;
  const token = user?.accessToken;
  const tenantId = user?.tenantId;

  const [filters, setFilters] = useState<CalendarListFilters>({
    page: 1,
    per_page: 20,
    start_date: new Date().toISOString().split("T")[0],
    end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
      .toISOString()
      .split("T")[0],
  });
  const [searchQuery, setSearchQuery] = useState("");

  // Queries
  const eventsQuery = useCalendarEvents(filters, token, tenantId);
  const statsQuery = useCalendarStats(undefined, token, tenantId);
  const calendarsQuery = useCalendars(token, tenantId);

  const handleSearch = () => {
    setFilters((prev) => ({ ...prev, search: searchQuery, page: 1 }));
  };

  const shiftDateRange = (days: number) => {
    const currentStart = new Date(filters.start_date || Date.now());
    const currentEnd = new Date(filters.end_date || Date.now());
    const newStart = new Date(currentStart.getTime() + days * 24 * 60 * 60 * 1000);
    const newEnd = new Date(currentEnd.getTime() + days * 24 * 60 * 60 * 1000);

    setFilters((prev) => ({
      ...prev,
      start_date: newStart.toISOString().split("T")[0],
      end_date: newEnd.toISOString().split("T")[0],
      page: 1,
    }));
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Agenda</h1>
          <p className="text-neutral-500 text-sm mt-1">
            Événements synchronisés depuis Google Calendar et Outlook
          </p>
        </div>
        <button
          onClick={() => router.push("/dashboard/admin/integrations")}
          className="btn-secondary"
        >
          Gérer les intégrations
        </button>
      </div>

      {/* Stats */}
      {statsQuery.data && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 bg-blue-50 rounded-lg">
                <CalendarIcon className="w-5 h-5 text-blue-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-neutral-900">
              {statsQuery.data.total_events}
            </p>
            <p className="text-sm text-neutral-500">Total événements</p>
          </div>

          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 bg-green-50 rounded-lg">
                <Clock className="w-5 h-5 text-green-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-neutral-900">
              {statsQuery.data.today_events}
            </p>
            <p className="text-sm text-neutral-500">Aujourd'hui</p>
          </div>

          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 bg-purple-50 rounded-lg">
                <CalendarIcon className="w-5 h-5 text-purple-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-neutral-900">
              {statsQuery.data.this_week_events}
            </p>
            <p className="text-sm text-neutral-500">Cette semaine</p>
          </div>

          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 bg-orange-50 rounded-lg">
                <CalendarIcon className="w-5 h-5 text-orange-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-neutral-900">
              {statsQuery.data.this_month_events}
            </p>
            <p className="text-sm text-neutral-500">Ce mois-ci</p>
          </div>

          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 bg-teal-50 rounded-lg">
                <Users className="w-5 h-5 text-teal-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-neutral-900">
              {statsQuery.data.linked_to_cases}
            </p>
            <p className="text-sm text-neutral-500">Liés aux dossiers</p>
          </div>
        </div>
      )}

      {/* Search and filters */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="flex-1 flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Rechercher un événement..."
            className="input flex-1"
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <button onClick={handleSearch} className="btn-primary px-4">
            <Search className="w-4 h-4" />
          </button>
        </div>

        <div className="flex gap-2">
          {calendarsQuery.data && calendarsQuery.data.items.length > 0 && (
            <select
              className="input"
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  calendar_id: e.target.value || undefined,
                  page: 1,
                }))
              }
            >
              <option value="">Tous les calendriers</option>
              {calendarsQuery.data.items.map((cal) => (
                <option key={cal.id} value={cal.id}>
                  {cal.name} ({cal.email_address})
                </option>
              ))}
            </select>
          )}

          <select
            className="input"
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                status: e.target.value as any || undefined,
                page: 1,
              }))
            }
          >
            <option value="">Tous les statuts</option>
            <option value="confirmed">Confirmés</option>
            <option value="tentative">Provisoires</option>
            <option value="cancelled">Annulés</option>
          </select>
        </div>
      </div>

      {/* Date range navigation */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => shiftDateRange(-30)}
          className="btn-secondary flex items-center gap-2"
        >
          <ChevronLeft className="w-4 h-4" />
          30 jours précédents
        </button>
        <div className="text-sm text-neutral-600">
          {new Date(filters.start_date || Date.now()).toLocaleDateString("fr-BE")} -{" "}
          {new Date(filters.end_date || Date.now()).toLocaleDateString("fr-BE")}
        </div>
        <button
          onClick={() => shiftDateRange(30)}
          className="btn-secondary flex items-center gap-2"
        >
          30 jours suivants
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Loading */}
      {eventsQuery.isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
        </div>
      )}

      {/* Error */}
      {eventsQuery.isError && (
        <div className="bg-red-50 rounded-lg p-6 border border-red-200">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-6 w-6 text-red-600" />
            <div>
              <h3 className="font-semibold text-red-900">Erreur de chargement</h3>
              <p className="text-sm text-red-700 mt-1">
                Impossible de charger les événements.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {eventsQuery.data && eventsQuery.data.items.length === 0 && (
        <div className="bg-white rounded-lg p-12 text-center border border-neutral-200">
          <CalendarIcon className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-neutral-600 mb-2">
            Aucun événement
          </h3>
          <p className="text-neutral-500">
            {filters.search
              ? "Aucun résultat pour cette recherche"
              : "Aucun événement pour cette période"}
          </p>
        </div>
      )}

      {/* Events list */}
      {eventsQuery.data && eventsQuery.data.items.length > 0 && (
        <div className="space-y-2">
          {eventsQuery.data.items.map((event) => {
            const StatusIcon = STATUS_ICONS[event.status];
            const startTime = new Date(event.start_time);
            const endTime = new Date(event.end_time);

            return (
              <div
                key={event.id}
                className="card hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => router.push(`/dashboard/calendar/${event.id}`)}
              >
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-purple-50 rounded-lg flex-shrink-0">
                    <CalendarIcon className="w-5 h-5 text-purple-600" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-semibold text-neutral-900">
                            {event.title || "(Sans titre)"}
                          </h3>
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[event.status]}`}
                          >
                            <StatusIcon className="w-3 h-3 inline mr-1" />
                            {STATUS_LABELS[event.status]}
                          </span>
                        </div>
                        <div className="flex flex-col gap-1 text-sm text-neutral-600">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5" />
                            {event.is_all_day
                              ? "Toute la journée"
                              : `${startTime.toLocaleTimeString("fr-BE", {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })} - ${endTime.toLocaleTimeString("fr-BE", {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}`}
                          </span>
                          {event.location && (
                            <span className="flex items-center gap-1">
                              <MapPin className="w-3.5 h-3.5" />
                              {event.location}
                            </span>
                          )}
                          {event.attendees.length > 0 && (
                            <span className="flex items-center gap-1">
                              <Users className="w-3.5 h-3.5" />
                              {event.attendees.length} participant
                              {event.attendees.length > 1 ? "s" : ""}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="text-xs text-neutral-500 block">
                          {startTime.toLocaleDateString("fr-BE", {
                            weekday: "short",
                            day: "numeric",
                            month: "short",
                          })}
                        </span>
                        {event.is_recurring && (
                          <span className="text-xs text-neutral-400 block mt-1">
                            Récurrent
                          </span>
                        )}
                      </div>
                    </div>

                    {event.description && (
                      <p className="text-sm text-neutral-600 line-clamp-2 mt-2">
                        {event.description}
                      </p>
                    )}

                    {event.case_id && (
                      <div className="flex items-center gap-2 mt-2">
                        <span className="px-2 py-1 bg-accent-50 text-accent-700 rounded text-xs font-medium">
                          Dossier: {event.case_title || event.case_id.slice(0, 8)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {eventsQuery.data && eventsQuery.data.total > eventsQuery.data.per_page && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() =>
              setFilters((prev) => ({ ...prev, page: (prev.page || 1) - 1 }))
            }
            disabled={(filters.page || 1) <= 1}
            className="btn-secondary disabled:opacity-50"
          >
            Précédent
          </button>
          <span className="text-sm text-neutral-600">
            Page {filters.page || 1} sur{" "}
            {Math.ceil(eventsQuery.data.total / eventsQuery.data.per_page)}
          </span>
          <button
            onClick={() =>
              setFilters((prev) => ({ ...prev, page: (prev.page || 1) + 1 }))
            }
            disabled={
              (filters.page || 1) >=
              Math.ceil(eventsQuery.data.total / eventsQuery.data.per_page)
            }
            className="btn-secondary disabled:opacity-50"
          >
            Suivant
          </button>
        </div>
      )}
    </div>
  );
}
