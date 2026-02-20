"use client";

import { useAuth } from "@/lib/useAuth";
import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  Calendar as CalendarIcon,
  Clock,
  MapPin,
  Users,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  Scale,
  Briefcase,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import {
  LoadingSkeleton,
  ErrorState,
  EmptyState,
  StatCard,
  Button,
  Card,
  Badge,
} from "@/components/ui";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

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

interface Deadline {
  title: string;
  date: string;
  days_remaining: number;
  urgency: "critical" | "urgent" | "attention" | "normal";
  case_id: string | null;
  case_title: string | null;
  legal_basis: string | null;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const generateMockDeadlines = (): Deadline[] => [
  {
    title: "Delai d'appel - Jugement TPI Bruxelles",
    date: new Date(Date.now() + 2 * 86400000).toISOString().split("T")[0],
    days_remaining: 2,
    urgency: "critical",
    case_id: "mock-1",
    case_title: "Dupont c/ SA Construct",
    legal_basis: "Art. 1051 C.J.",
  },
  {
    title: "Depot conclusions en reponse",
    date: new Date(Date.now() + 5 * 86400000).toISOString().split("T")[0],
    days_remaining: 5,
    urgency: "urgent",
    case_id: "mock-2",
    case_title: "Janssens - Succession",
    legal_basis: "Calendrier de mise en etat",
  },
  {
    title: "Delai de citation",
    date: new Date(Date.now() + 6 * 86400000).toISOString().split("T")[0],
    days_remaining: 6,
    urgency: "urgent",
    case_id: "mock-3",
    case_title: "SPRL Tech Innov",
    legal_basis: "Art. 707 C.J.",
  },
  {
    title: "Prescription action civile",
    date: new Date(Date.now() + 12 * 86400000).toISOString().split("T")[0],
    days_remaining: 12,
    urgency: "attention",
    case_id: "mock-1",
    case_title: "Dupont c/ SA Construct",
    legal_basis: "Art. 2262bis C.C.",
  },
  {
    title: "Audience de plaidoirie",
    date: new Date(Date.now() + 21 * 86400000).toISOString().split("T")[0],
    days_remaining: 21,
    urgency: "normal",
    case_id: "mock-4",
    case_title: "Maes - Licenciement",
    legal_basis: null,
  },
];

/** Map urgency level to colour classes used throughout the page. */
const urgencyColor = (urgency: Deadline["urgency"]) => {
  switch (urgency) {
    case "critical":
      return {
        bg: "bg-red-50",
        border: "border-red-500",
        text: "text-red-700",
        dot: "bg-red-500",
        badge: "danger" as const,
        label: "Critique",
      };
    case "urgent":
      return {
        bg: "bg-amber-50",
        border: "border-amber-500",
        text: "text-amber-700",
        dot: "bg-amber-500",
        badge: "warning" as const,
        label: "Urgent",
      };
    case "attention":
      return {
        bg: "bg-yellow-50",
        border: "border-yellow-500",
        text: "text-yellow-700",
        dot: "bg-yellow-500",
        badge: "warning" as const,
        label: "Attention",
      };
    default:
      return {
        bg: "bg-neutral-50",
        border: "border-neutral-400",
        text: "text-neutral-600",
        dot: "bg-neutral-400",
        badge: "default" as const,
        label: "Normal",
      };
  }
};

/** Format a date string to French locale. */
const formatDateFr = (dateStr: string) =>
  new Date(dateStr).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

/** Get the Monday-based ISO week number for a date. */
const getWeekNumber = (d: Date): number => {
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function CalendarPage() {
  const { accessToken, tenantId } = useAuth();
  const router = useRouter();

  /* ---- existing state ---- */
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [stats, setStats] = useState<CalendarStats | null>(null);
  const [dateAfter, setDateAfter] = useState(new Date().toISOString());
  const [dateBefore, setDateBefore] = useState(
    new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  );
  const [syncing, setSyncing] = useState(false);

  /* ---- deadline state ---- */
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [deadlinesLoading, setDeadlinesLoading] = useState(false);

  /* ---- existing data fetching ---- */

  useEffect(() => {
    async function fetchData() {
      if (!accessToken) return;
      try {
        setLoading(true);
        setError("");
        const query = `?after=${encodeURIComponent(dateAfter)}&before=${encodeURIComponent(dateBefore)}`;
        const res = await apiFetch<CalendarEvent[]>(
          `/calendar/events${query}`,
          accessToken,
        );
        setEvents(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur de chargement");
      } finally {
        setLoading(false);
      }
    }

    if (accessToken) {
      fetchData();
    }
  }, [accessToken, dateAfter, dateBefore]);

  useEffect(() => {
    async function fetchStats() {
      if (!accessToken) return;
      try {
        const res = await apiFetch<CalendarStats>(
          "/calendar/stats",
          accessToken,
        );
        setStats(res);
      } catch {
        // Stats fetch failed silently -- non-critical
      }
    }

    if (accessToken) {
      fetchStats();
    }
  }, [accessToken]);

  /* ---- deadline fetching ---- */

  useEffect(() => {
    async function fetchDeadlines() {
      if (!accessToken) return;
      try {
        setDeadlinesLoading(true);
        const data = await apiFetch<Deadline[]>(
          "/brain/deadlines?days_ahead=30",
          accessToken,
          { tenantId },
        );
        setDeadlines(data);
      } catch {
        // Fallback to mock deadlines
        setDeadlines(generateMockDeadlines());
      } finally {
        setDeadlinesLoading(false);
      }
    }

    if (accessToken) {
      fetchDeadlines();
    }
  }, [accessToken, tenantId]);

  /* ---- sync handler ---- */

  const handleSync = async () => {
    if (!accessToken) return;
    try {
      setSyncing(true);
      await apiFetch("/calendar/sync", accessToken, { method: "POST" });
    } catch {
      // Sync failed silently -- non-critical
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

  /* ---- derived deadline data ---- */

  /** Deadlines sorted by urgency priority then date. */
  const sortedDeadlines = useMemo(() => {
    const order: Record<string, number> = {
      critical: 0,
      urgent: 1,
      attention: 2,
      normal: 3,
    };
    return [...deadlines].sort(
      (a, b) => (order[a.urgency] ?? 4) - (order[b.urgency] ?? 4) || a.days_remaining - b.days_remaining,
    );
  }, [deadlines]);

  /** Next 5 critical or urgent deadlines. */
  const criticalDeadlines = useMemo(
    () =>
      sortedDeadlines
        .filter((d) => d.urgency === "critical" || d.urgency === "urgent")
        .slice(0, 5),
    [sortedDeadlines],
  );

  /** Workload per week for the next 4 weeks. */
  const weeklyWorkload = useMemo(() => {
    const today = new Date();
    const weeks: { weekLabel: string; count: number; overloaded: boolean }[] = [];

    for (let w = 0; w < 4; w++) {
      const weekStart = new Date(today);
      weekStart.setDate(today.getDate() + w * 7);
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);

      const count = deadlines.filter((d) => {
        const dd = new Date(d.date);
        return dd >= weekStart && dd <= weekEnd;
      }).length;

      const weekNum = getWeekNumber(weekStart);
      weeks.push({
        weekLabel: `Sem. ${weekNum}`,
        count,
        overloaded: count > 5,
      });
    }

    return weeks;
  }, [deadlines]);

  /** Map deadline dates for quick look-up when rendering event cards. */
  const deadlineByDate = useMemo(() => {
    const map = new Map<string, Deadline>();
    for (const d of deadlines) {
      if (!map.has(d.date)) map.set(d.date, d);
    }
    return map;
  }, [deadlines]);

  /* ---- render ---- */

  return (
    <div>
      {/* ============================================================ */}
      {/*  Header                                                       */}
      {/* ============================================================ */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Agenda</h1>
          <p className="text-neutral-500 text-sm mt-1">
            Evenements synchronises depuis Google Calendar et Outlook
          </p>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="btn-primary"
        >
          {syncing ? "Synchronisation..." : "Synchroniser"}
        </button>
      </div>

      {/* ============================================================ */}
      {/*  1. Legal Deadline Banner -- Echeances juridiques             */}
      {/* ============================================================ */}
      {!deadlinesLoading && sortedDeadlines.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Scale className="w-5 h-5 text-neutral-700" />
            <h2 className="text-lg font-semibold text-neutral-900">
              Echeances juridiques
            </h2>
            <Badge variant="neutral" size="sm">
              {sortedDeadlines.length}
            </Badge>
          </div>

          <div className="space-y-2">
            {sortedDeadlines.map((deadline, idx) => {
              const colors = urgencyColor(deadline.urgency);
              return (
                <div
                  key={`${deadline.title}-${idx}`}
                  className={`flex items-center gap-4 rounded border-l-4 ${colors.border} ${colors.bg} px-4 py-3 transition-shadow hover:shadow-sm`}
                >
                  {/* Urgency dot */}
                  <span
                    className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${colors.dot} ${
                      deadline.urgency === "critical"
                        ? "animate-pulse-subtle"
                        : ""
                    }`}
                  />

                  {/* Main content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-neutral-900 truncate">
                        {deadline.title}
                      </span>
                      <Badge
                        variant={colors.badge}
                        size="sm"
                      >
                        {colors.label}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-4 text-sm text-neutral-600 mt-1 flex-wrap">
                      {deadline.case_title && (
                        <span
                          className="flex items-center gap-1 cursor-pointer hover:text-neutral-900"
                          onClick={() => {
                            if (deadline.case_id) {
                              router.push(
                                `/dashboard/cases/${deadline.case_id}`,
                              );
                            }
                          }}
                        >
                          <Briefcase className="w-3.5 h-3.5" />
                          {deadline.case_title}
                        </span>
                      )}
                      {deadline.legal_basis && (
                        <span className="flex items-center gap-1">
                          <Scale className="w-3.5 h-3.5" />
                          {deadline.legal_basis}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Right: date & countdown */}
                  <div className="text-right flex-shrink-0">
                    <div className="text-sm font-medium text-neutral-800">
                      {formatDateFr(deadline.date)}
                    </div>
                    <div
                      className={`text-xs font-semibold mt-0.5 ${colors.text}`}
                    >
                      {deadline.days_remaining === 0
                        ? "Aujourd'hui"
                        : deadline.days_remaining === 1
                          ? "Demain"
                          : `${deadline.days_remaining} jours`}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {deadlinesLoading && (
        <div className="mb-6">
          <div className="h-4 w-48 bg-neutral-200 rounded animate-shimmer mb-3" />
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-16 bg-neutral-100 rounded animate-shimmer"
              />
            ))}
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/*  Stats cards (existing)                                       */}
      {/* ============================================================ */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card className="hover:shadow-lg transition-shadow">
            <StatCard
              title="Total evenements"
              value={stats.total_events}
              icon={<CalendarIcon className="w-5 h-5" />}
              color="accent"
            />
          </Card>
          <Card className="hover:shadow-lg transition-shadow">
            <StatCard
              title="Aujourd'hui"
              value={stats.today_events}
              icon={<Clock className="w-5 h-5" />}
              color="success"
            />
          </Card>
          <Card className="hover:shadow-lg transition-shadow">
            <StatCard
              title="A venir (7 jours)"
              value={stats.upcoming_week}
              icon={<Users className="w-5 h-5" />}
              color="warning"
            />
          </Card>
        </div>
      )}

      {/* ============================================================ */}
      {/*  Date navigation (existing)                                   */}
      {/* ============================================================ */}
      <div className="flex items-center justify-between mb-6">
        <Button
          variant="secondary"
          size="sm"
          icon={<ChevronLeft className="w-4 h-4" />}
          onClick={() => shiftDate(-30)}
        >
          -30 jours
        </Button>
        <div className="text-sm text-neutral-600 font-medium">
          {new Date(dateAfter).toLocaleDateString("fr-FR")} -{" "}
          {new Date(dateBefore).toLocaleDateString("fr-FR")}
        </div>
        <Button
          variant="secondary"
          size="sm"
          icon={<ChevronRight className="w-4 h-4" />}
          onClick={() => shiftDate(30)}
        >
          +30 jours
        </Button>
      </div>

      {/* ============================================================ */}
      {/*  Event list (existing, enhanced with urgency indicators)      */}
      {/* ============================================================ */}
      {loading && <LoadingSkeleton />}

      {error && <ErrorState message={error} />}

      {!loading && events.length === 0 && (
        <EmptyState
          icon={<CalendarIcon className="w-12 h-12" />}
          title="Aucun evenement"
          description="Aucun evenement pour cette periode"
        />
      )}

      {!loading && events.length > 0 && (
        <div className="space-y-3">
          {events.map((event) => {
            const matchedDeadline = deadlineByDate.get(event.date);
            const dlColors = matchedDeadline
              ? urgencyColor(matchedDeadline.urgency)
              : null;

            return (
              <Card
                key={event.id}
                hover
                onClick={() =>
                  router.push(`/dashboard/calendar/${event.id}`)
                }
                className={
                  dlColors
                    ? `border-l-4 ${dlColors.border}`
                    : ""
                }
              >
                <div className="flex items-start gap-4">
                  <div
                    className={`p-2 rounded ${
                      dlColors
                        ? `${dlColors.bg}`
                        : "bg-accent-50"
                    }`}
                  >
                    <CalendarIcon
                      className={`w-5 h-5 ${
                        dlColors
                          ? dlColors.text
                          : "text-accent-600"
                      }`}
                    />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-medium text-neutral-900">
                        {event.title}
                      </h3>
                      {matchedDeadline && (
                        <Badge
                          variant={dlColors!.badge}
                          size="sm"
                          dot
                        >
                          Echeance juridique
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-neutral-600 mt-1 flex-wrap">
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
                          {event.attendees.length} participant
                          {event.attendees.length > 1 ? "s" : ""}
                        </span>
                      )}
                      {matchedDeadline?.case_title && (
                        <span
                          className="flex items-center gap-1 cursor-pointer hover:text-neutral-900"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (matchedDeadline.case_id) {
                              router.push(
                                `/dashboard/cases/${matchedDeadline.case_id}`,
                              );
                            }
                          }}
                        >
                          <Briefcase className="w-3.5 h-3.5" />
                          {matchedDeadline.case_title}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* ============================================================ */}
      {/*  3. Deadline Intelligence Cards                               */}
      {/* ============================================================ */}
      {!deadlinesLoading && deadlines.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
          {/* ---- Left: Prochaines echeances critiques ---- */}
          <Card
            header={
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                <h3 className="font-semibold text-neutral-900">
                  Prochaines echeances critiques
                </h3>
              </div>
            }
          >
            {criticalDeadlines.length === 0 ? (
              <p className="text-sm text-neutral-500">
                Aucune echeance critique ou urgente dans les 30 prochains jours.
              </p>
            ) : (
              <div className="space-y-3">
                {criticalDeadlines.map((deadline, idx) => {
                  const colors = urgencyColor(deadline.urgency);
                  return (
                    <div
                      key={`crit-${idx}`}
                      className={`flex items-start gap-3 rounded p-3 ${colors.bg} border-l-4 ${colors.border}`}
                    >
                      <span
                        className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${colors.dot}`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-neutral-900 truncate">
                          {deadline.title}
                        </p>
                        {deadline.case_title && (
                          <p
                            className="text-xs text-neutral-600 mt-0.5 cursor-pointer hover:text-neutral-900 truncate"
                            onClick={() => {
                              if (deadline.case_id) {
                                router.push(
                                  `/dashboard/cases/${deadline.case_id}`,
                                );
                              }
                            }}
                          >
                            <Briefcase className="w-3 h-3 inline mr-1" />
                            {deadline.case_title}
                          </p>
                        )}
                        {deadline.legal_basis && (
                          <p className="text-xs text-neutral-500 mt-0.5">
                            <Scale className="w-3 h-3 inline mr-1" />
                            {deadline.legal_basis}
                          </p>
                        )}
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className="text-xs text-neutral-600">
                          {formatDateFr(deadline.date)}
                        </div>
                        <div
                          className={`text-xs font-bold mt-0.5 ${colors.text}`}
                        >
                          {deadline.days_remaining === 0
                            ? "Aujourd'hui"
                            : deadline.days_remaining === 1
                              ? "Demain"
                              : `${deadline.days_remaining}j`}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          {/* ---- Right: Semaines chargees ---- */}
          <Card
            header={
              <div className="flex items-center gap-2">
                <CalendarIcon className="w-5 h-5 text-neutral-700" />
                <h3 className="font-semibold text-neutral-900">
                  Semaines chargees
                </h3>
              </div>
            }
          >
            <p className="text-sm text-neutral-500 mb-4">
              Charge des echeances sur les 4 prochaines semaines
            </p>
            <div className="space-y-3">
              {weeklyWorkload.map((week, idx) => {
                const maxBar = Math.max(
                  ...weeklyWorkload.map((w) => w.count),
                  1,
                );
                const pct = Math.round((week.count / maxBar) * 100);

                return (
                  <div key={idx} className="flex items-center gap-3">
                    <span className="text-sm font-medium text-neutral-700 w-16 flex-shrink-0">
                      {week.weekLabel}
                    </span>
                    <div className="flex-1 bg-neutral-100 rounded-full h-5 relative overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          week.overloaded
                            ? "bg-red-500"
                            : week.count > 3
                              ? "bg-amber-500"
                              : "bg-accent-500"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span
                      className={`text-sm font-semibold w-12 text-right ${
                        week.overloaded
                          ? "text-red-600"
                          : "text-neutral-700"
                      }`}
                    >
                      {week.count}
                    </span>
                    {week.overloaded && (
                      <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
                    )}
                  </div>
                );
              })}
            </div>
            {weeklyWorkload.some((w) => w.overloaded) && (
              <p className="text-xs text-red-600 mt-3 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                Certaines semaines depassent 5 echeances. Pensez a repartir la
                charge.
              </p>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
