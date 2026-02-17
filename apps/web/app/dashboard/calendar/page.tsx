"use client";

import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Calendar as CalendarIcon, Clock, MapPin, Users, ChevronLeft, ChevronRight } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, StatCard } from "@/components/ui";

interface CalendarEvent {
  id: string;
  title: string;
  start_time: string;
  location?: string;
  attendees: string[];
  date: string;
  time: string;
}

interface CalendarStats {
  total_events: number;
  today_events: number;
  upcoming_week: number;
}

export default function CalendarPage() {
  const { data: session } = useSession();
  const router = useRouter();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [stats, setStats] = useState<CalendarStats | null>(null);
  const [dateAfter, setDateAfter] = useState(new Date().toISOString());
  const [dateBefore, setDateBefore] = useState(
    new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
  );
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    async function fetchData() {
      if (!session?.user?.accessToken) return;
      try {
        setLoading(true);
        setError("");
        const query = `?after=${encodeURIComponent(dateAfter)}&before=${encodeURIComponent(dateBefore)}`;
        const res = await apiFetch<CalendarEvent[]>(`/calendar/events${query}`, session.user.accessToken);
        setEvents(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur de chargement");
      } finally {
        setLoading(false);
      }
    }

    if (session?.user?.accessToken) {
      fetchData();
    }
  }, [session?.user?.accessToken, dateAfter, dateBefore]);

  useEffect(() => {
    async function fetchStats() {
      if (!session?.user?.accessToken) return;
      try {
        const res = await apiFetch<CalendarStats>("/calendar/stats", session.user.accessToken);
        setStats(res);
      } catch (err) {
        console.error("Erreur stats:", err);
      }
    }

    if (session?.user?.accessToken) {
      fetchStats();
    }
  }, [session?.user?.accessToken]);

  const handleSync = async () => {
    if (!session?.user?.accessToken) return;
    try {
      setSyncing(true);
      await apiFetch("/calendar/sync", session.user.accessToken, { method: "POST" });
    } catch (err) {
      console.error("Erreur sync:", err);
    } finally {
      setSyncing(false);
    }
  };

  const shiftDate = (days: number) => {
    const newAfter = new Date(dateAfter);
    newAfter.setDate(newAfter.getDate() + days);
    const newBefore = new Date(dateBefore);
    newBefore.setDate(newBefore.getDate() + days);
    setDateAfter(newAfter.toISOString());
    setDateBefore(newBefore.toISOString());
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Agenda</h1>
          <p className="text-neutral-500 text-sm mt-1">
            Événements synchronisés depuis Google Calendar et Outlook
          </p>
        </div>
        <button onClick={handleSync} disabled={syncing} className="btn-primary">
          {syncing ? "Synchronisation..." : "Synchroniser"}
        </button>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <StatCard
            title="Total événements"
            value={stats.total_events}
            icon={<CalendarIcon className="w-5 h-5" />}
            color="accent"
          />
          <StatCard
            title="Aujourd'hui"
            value={stats.today_events}
            icon={<Clock className="w-5 h-5" />}
            color="success"
          />
          <StatCard
            title="À venir (7 jours)"
            value={stats.upcoming_week}
            icon={<Users className="w-5 h-5" />}
            color="warning"
          />
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <button onClick={() => shiftDate(-30)} className="btn-secondary flex items-center gap-2">
          <ChevronLeft className="w-4 h-4" />
          -30 jours
        </button>
        <div className="text-sm text-neutral-600">
          {new Date(dateAfter).toLocaleDateString("fr-FR")} - {new Date(dateBefore).toLocaleDateString("fr-FR")}
        </div>
        <button onClick={() => shiftDate(30)} className="btn-secondary flex items-center gap-2">
          +30 jours
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {loading && <LoadingSkeleton />}

      {error && <ErrorState message={error} />}

      {!loading && events.length === 0 && (
        <EmptyState
          icon={<CalendarIcon className="w-12 h-12" />}
          title="Aucun événement"
          description="Aucun événement pour cette période"
        />
      )}

      {!loading && events.length > 0 && (
        <div className="space-y-3">
          {events.map((event) => (
            <div
              key={event.id}
              className="card p-4 cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => router.push(`/dashboard/calendar/${event.id}`)}
            >
              <div className="flex items-start gap-4">
                <div className="p-2 bg-accent-50 rounded">
                  <CalendarIcon className="w-5 h-5 text-accent-600" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-neutral-900">{event.title}</h3>
                  <div className="flex items-center gap-4 text-sm text-neutral-600 mt-1">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {event.time}
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
                        {event.attendees.length} participant{event.attendees.length > 1 ? "s" : ""}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
