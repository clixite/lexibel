"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState, useCallback } from "react";
import {
  Clock,
  Loader2,
  ChevronDown,
  Mail,
  Phone,
  FileText,
  PenLine,
  AlertTriangle,
  X,
  Link2,
} from "lucide-react";
import { apiFetch } from "@/lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface CaseOption {
  id: string;
  reference: string;
  title: string;
}

interface CaseListResponse {
  items: CaseOption[];
  total: number;
}

interface TimelineEvent {
  id: string;
  case_id: string;
  source: string;
  event_type: string;
  title: string;
  body: string | null;
  occurred_at: string;
  metadata: Record<string, any> | null;
  created_by: string | null;
  evidence_links: string[] | null;
}

interface TimelineResponse {
  items: TimelineEvent[];
  total: number;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const EVENT_TYPE_LABELS: Record<string, string> = {
  email_received: "E-mail reçu",
  email_sent: "E-mail envoyé",
  call_inbound: "Appel entrant",
  call_outbound: "Appel sortant",
  document_received: "Document reçu",
  document_sent: "Document envoyé",
  note: "Note interne",
  meeting: "Réunion",
  hearing: "Audience",
  status_change: "Changement de statut",
  assignment: "Attribution",
  deadline: "Échéance",
  payment: "Paiement",
  other: "Autre",
};

const SOURCE_CONFIG: Record<
  string,
  { color: string; dotColor: string; icon: React.ReactNode }
> = {
  OUTLOOK: {
    color: "text-accent",
    dotColor: "bg-accent",
    icon: <Mail className="w-4 h-4" />,
  },
  email: {
    color: "text-accent",
    dotColor: "bg-accent",
    icon: <Mail className="w-4 h-4" />,
  },
  RINGOVER: {
    color: "text-success",
    dotColor: "bg-success",
    icon: <Phone className="w-4 h-4" />,
  },
  phone: {
    color: "text-success",
    dotColor: "bg-success",
    icon: <Phone className="w-4 h-4" />,
  },
  DPA: {
    color: "text-warning",
    dotColor: "bg-warning",
    icon: <FileText className="w-4 h-4" />,
  },
  document: {
    color: "text-warning",
    dotColor: "bg-warning",
    icon: <FileText className="w-4 h-4" />,
  },
  MANUAL: {
    color: "text-neutral-500",
    dotColor: "bg-neutral-400",
    icon: <PenLine className="w-4 h-4" />,
  },
};

const DEFAULT_SOURCE_CONFIG = {
  color: "text-neutral-500",
  dotColor: "bg-neutral-400",
  icon: <PenLine className="w-4 h-4" />,
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function getSourceConfig(source: string) {
  return SOURCE_CONFIG[source] || SOURCE_CONFIG[source.toUpperCase()] || DEFAULT_SOURCE_CONFIG;
}

function formatDateTimeFrBE(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("fr-BE", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDateGroupKey(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("fr-BE", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleTimeString("fr-BE", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function groupEventsByDate(
  events: TimelineEvent[],
): { date: string; events: TimelineEvent[] }[] {
  const groups: Map<string, TimelineEvent[]> = new Map();

  for (const event of events) {
    const key = formatDateGroupKey(event.occurred_at);
    if (!groups.has(key)) {
      groups.set(key, []);
    }
    groups.get(key)!.push(event);
  }

  return Array.from(groups.entries()).map(([date, events]) => ({
    date,
    events,
  }));
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function TimelinePage() {
  const { data: session } = useSession();

  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;
  const userId = (session?.user as any)?.id;

  /* --- State --- */
  const [cases, setCases] = useState<CaseOption[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>("");
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [totalEvents, setTotalEvents] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());

  const perPage = 50;

  /* --- Data loading --- */
  const loadCases = useCallback(() => {
    if (!token) return;
    apiFetch<CaseListResponse>("/cases", token, { tenantId })
      .then((data) => {
        setCases(data.items);
        if (data.items.length > 0 && !selectedCaseId) {
          setSelectedCaseId(data.items[0].id);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => {
        if (!selectedCaseId) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, tenantId]);

  const loadTimeline = useCallback(
    (caseId: string, pageNum: number, append: boolean = false) => {
      if (!token || !caseId) return;
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      setError(null);

      apiFetch<TimelineResponse>(
        `/cases/${caseId}/timeline?page=${pageNum}&per_page=${perPage}`,
        token,
        { tenantId },
      )
        .then((data) => {
          if (append) {
            setEvents((prev) => [...prev, ...data.items]);
          } else {
            setEvents(data.items);
          }
          setTotalEvents(data.total);
          setPage(pageNum);
        })
        .catch((err) => setError(err.message))
        .finally(() => {
          setLoading(false);
          setLoadingMore(false);
        });
    },
    [token, tenantId],
  );

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  useEffect(() => {
    if (selectedCaseId) {
      setEvents([]);
      loadTimeline(selectedCaseId, 1);
    }
  }, [selectedCaseId, loadTimeline]);

  /* --- Interactions --- */
  const handleCaseChange = (caseId: string) => {
    setSelectedCaseId(caseId);
    setExpandedEvents(new Set());
  };

  const toggleExpand = (eventId: string) => {
    setExpandedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
  };

  const handleLoadMore = () => {
    loadTimeline(selectedCaseId, page + 1, true);
  };

  const hasMore = events.length < totalEvents;
  const selectedCase = cases.find((c) => c.id === selectedCaseId);
  const groupedEvents = groupEventsByDate(events);

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-accent-50 flex items-center justify-center">
            <Clock className="w-5 h-5 text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-neutral-900">Timeline</h1>
          {totalEvents > 0 && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-accent-50 text-accent-700">
              {totalEvents} événement{totalEvents > 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      {/* Case selector */}
      <div className="bg-white rounded-lg shadow-subtle border border-neutral-100 p-4 mb-6">
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-neutral-700 whitespace-nowrap">
            Dossier :
          </label>
          <div className="relative flex-1 max-w-md">
            <select
              value={selectedCaseId}
              onChange={(e) => handleCaseChange(e.target.value)}
              className="input appearance-none pr-8"
              disabled={cases.length === 0}
            >
              {cases.length === 0 ? (
                <option value="">Aucun dossier disponible</option>
              ) : (
                cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.reference} — {c.title}
                  </option>
                ))
              )}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 pointer-events-none" />
          </div>
          {selectedCase && (
            <span className="text-xs text-neutral-400">
              Réf. {selectedCase.reference}
            </span>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-4 text-sm flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-auto text-danger-400 hover:text-danger-600"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-accent" />
        </div>
      )}

      {/* Empty state */}
      {!loading && events.length === 0 && (
        <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
          <div className="relative">
            <div className="absolute inset-0 opacity-[0.03]">
              <div
                className="w-full h-full"
                style={{
                  backgroundImage:
                    "radial-gradient(circle at 1px 1px, currentColor 1px, transparent 0)",
                  backgroundSize: "24px 24px",
                }}
              />
            </div>
            <div className="relative px-6 py-20 text-center">
              <div className="w-16 h-16 rounded-lg bg-accent-50 flex items-center justify-center mx-auto mb-5">
                <Clock className="w-8 h-8 text-accent" />
              </div>
              <h2 className="text-xl font-semibold text-neutral-900 mb-2">
                Aucun événement
              </h2>
              <p className="text-neutral-500 text-sm max-w-md mx-auto">
                {cases.length === 0
                  ? "Créez un dossier pour commencer à visualiser la timeline des interactions."
                  : "Ce dossier ne contient pas encore d'événements. Les interactions validées depuis l'inbox apparaîtront ici."}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Timeline */}
      {!loading && events.length > 0 && (
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[19px] top-0 bottom-0 w-0.5 bg-neutral-200" />

          {groupedEvents.map((group) => (
            <div key={group.date} className="mb-8">
              {/* Date header */}
              <div className="relative flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-neutral-100 border-2 border-white shadow-subtle flex items-center justify-center z-10">
                  <Clock className="w-4 h-4 text-neutral-500" />
                </div>
                <h3 className="text-sm font-semibold text-neutral-700 capitalize">
                  {group.date}
                </h3>
              </div>

              {/* Events */}
              <div className="space-y-3 ml-[19px] pl-8 border-l-0">
                {group.events.map((event) => {
                  const config = getSourceConfig(event.source);
                  const isExpanded = expandedEvents.has(event.id);
                  const hasBody = event.body && event.body.trim().length > 0;
                  const bodyTruncated =
                    hasBody && !isExpanded && event.body!.length > 200;

                  return (
                    <div
                      key={event.id}
                      className="relative bg-white rounded-lg shadow-subtle border border-neutral-100 p-4 hover:border-neutral-200 transition-colors duration-150"
                    >
                      {/* Dot on timeline */}
                      <div
                        className={`absolute -left-[25px] top-5 w-3 h-3 rounded-full border-2 border-white shadow-sm ${config.dotColor}`}
                      />

                      <div className="flex items-start gap-3">
                        {/* Source icon */}
                        <div
                          className={`w-8 h-8 rounded-md bg-neutral-50 flex items-center justify-center flex-shrink-0 ${config.color}`}
                        >
                          {config.icon}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span
                                  className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-neutral-100 text-neutral-600`}
                                >
                                  {EVENT_TYPE_LABELS[event.event_type] ||
                                    event.event_type}
                                </span>
                                <span className="text-xs text-neutral-400 uppercase tracking-wide">
                                  {event.source}
                                </span>
                              </div>
                              <h4 className="text-sm font-semibold text-neutral-900 mt-1.5">
                                {event.title}
                              </h4>
                            </div>
                            <span className="text-xs text-neutral-400 whitespace-nowrap flex-shrink-0">
                              {formatTime(event.occurred_at)}
                            </span>
                          </div>

                          {/* Body */}
                          {hasBody && (
                            <div className="mt-2">
                              <p className="text-sm text-neutral-600 leading-relaxed">
                                {isExpanded
                                  ? event.body
                                  : bodyTruncated
                                    ? `${event.body!.slice(0, 200)}...`
                                    : event.body}
                              </p>
                              {bodyTruncated && (
                                <button
                                  onClick={() => toggleExpand(event.id)}
                                  className="text-xs text-accent hover:text-accent-700 font-medium mt-1"
                                >
                                  {isExpanded
                                    ? "Voir moins"
                                    : "Voir plus"}
                                </button>
                              )}
                              {isExpanded && event.body!.length > 200 && (
                                <button
                                  onClick={() => toggleExpand(event.id)}
                                  className="text-xs text-accent hover:text-accent-700 font-medium mt-1"
                                >
                                  Voir moins
                                </button>
                              )}
                            </div>
                          )}

                          {/* Evidence links */}
                          {event.evidence_links &&
                            event.evidence_links.length > 0 && (
                              <div className="flex items-center gap-2 mt-2 flex-wrap">
                                {event.evidence_links.map((link, idx) => (
                                  <a
                                    key={idx}
                                    href={link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs bg-accent-50 text-accent-700 hover:bg-accent-100 transition-colors"
                                  >
                                    <Link2 className="w-3 h-3" />
                                    Pièce {idx + 1}
                                  </a>
                                ))}
                              </div>
                            )}

                          {/* Metadata footer */}
                          <div className="flex items-center gap-3 mt-2 text-xs text-neutral-400">
                            <span>
                              {formatDateTimeFrBE(event.occurred_at)}
                            </span>
                            {event.created_by && (
                              <>
                                <span className="w-1 h-1 rounded-full bg-neutral-300" />
                                <span>Par {event.created_by}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}

          {/* Load more */}
          {hasMore && (
            <div className="flex justify-center mt-6">
              <button
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="btn-secondary flex items-center gap-2 disabled:opacity-50"
              >
                {loadingMore ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
                Charger plus d&apos;événements
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
