"use client";

import { useAuth } from "@/lib/useAuth";
import { useEffect, useState, useCallback } from "react";
import {
  Briefcase,
  Clock,
  Mail,
  Phone,
  FileCheck,
  CalendarDays,
  FolderOpen,
  Inbox as InboxIcon,
  TrendingUp,
  AlertTriangle,
  FileEdit,
  Lightbulb,
  MessageSquare,
  Brain,
  ShieldAlert,
  Activity,
  CheckCircle2,
  XCircle,
  Timer,
  ChevronRight,
  X,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import {
  LoadingSkeleton,
  ErrorState,
  Card,
  Badge,
  EmptyState,
} from "@/components/ui";

/* ─────────────────────────── Types ─────────────────────────── */

interface RiskDistribution {
  low: number;
  medium: number;
  high: number;
  critical: number;
}

interface CriticalDeadline {
  id: string;
  title: string;
  case_name: string;
  due_date: string;
  days_remaining: number;
  urgency: "critical" | "urgent" | "attention" | "normal";
}

interface BrainAction {
  id: string;
  type: "alert" | "draft" | "suggestion" | "follow_up";
  title: string;
  description: string;
  priority: "critical" | "high" | "medium" | "low";
  case_name?: string;
}

interface BrainInsight {
  id: string;
  severity: "critical" | "high" | "medium" | "low";
  title: string;
  description: string;
  case_id?: string;
  case_name?: string;
}

interface WorkloadWeek {
  week_label: string;
  deadline_count: number;
  capacity: number;
}

interface BrainSummaryResponse {
  total_active_cases: number;
  risk_distribution: RiskDistribution;
  critical_deadlines: CriticalDeadline[];
  pending_actions: BrainAction[];
  recent_insights: BrainInsight[];
  workload_next_weeks: WorkloadWeek[];
  cases_needing_attention: number;
  health_score: number;
  stats: Record<string, number>;
}

interface RecentCase {
  id: string;
  title: string;
  status: string;
  updated_at: string;
  health_score?: number;
}

interface InboxItem {
  id: string;
  subject: string;
  source: string;
  from_name?: string;
}

interface DashboardResponse {
  stats?: {
    total_cases: number;
    total_contacts: number;
    monthly_hours: number;
    total_invoices: number;
    total_documents: number;
    pending_inbox: number;
  };
  items?: unknown[];
}

/* ─────────────────────────── Fallback Data ─────────────────────────── */

const FALLBACK_BRAIN: BrainSummaryResponse = {
  total_active_cases: 0,
  risk_distribution: { low: 0, medium: 0, high: 0, critical: 0 },
  critical_deadlines: [],
  pending_actions: [],
  recent_insights: [],
  workload_next_weeks: [],
  cases_needing_attention: 0,
  health_score: 0,
  stats: {},
};

const PLACEHOLDER_DEADLINES: CriticalDeadline[] = [
  {
    id: "ph-1",
    title: "Conclusions -- Dupont c/ Immobel",
    case_name: "Dupont c/ Immobel SA",
    due_date: "2026-02-21",
    days_remaining: 2,
    urgency: "critical",
  },
  {
    id: "ph-2",
    title: "Audience -- TPI Bruxelles",
    case_name: "TPI Bruxelles - Janssens",
    due_date: "2026-02-24",
    days_remaining: 5,
    urgency: "urgent",
  },
  {
    id: "ph-3",
    title: "Delai d'appel -- Janssens",
    case_name: "Janssens c/ Etat belge",
    due_date: "2026-02-28",
    days_remaining: 9,
    urgency: "attention",
  },
  {
    id: "ph-4",
    title: "Depot de bilan -- SA Construct",
    case_name: "SA Construct - Faillite",
    due_date: "2026-03-05",
    days_remaining: 14,
    urgency: "normal",
  },
  {
    id: "ph-5",
    title: "Mediation -- Famille Peeters",
    case_name: "Peeters - Divorce",
    due_date: "2026-03-10",
    days_remaining: 19,
    urgency: "normal",
  },
];

const PLACEHOLDER_ACTIONS: BrainAction[] = [
  {
    id: "pa-1",
    type: "alert",
    title: "Risque de prescription -- Dossier Lambert",
    description:
      "Le delai de prescription de 5 ans expire dans 12 jours. Une action en justice doit etre initiee avant le 3 mars 2026.",
    priority: "critical",
    case_name: "Lambert c/ AXA Belgium",
  },
  {
    id: "pa-2",
    type: "draft",
    title: "Projet de conclusions a relire",
    description:
      "Les conclusions de synthese pour le dossier Dupont c/ Immobel sont pretes pour relecture. Echeance de depot : 21 fevrier.",
    priority: "high",
    case_name: "Dupont c/ Immobel SA",
  },
  {
    id: "pa-3",
    type: "suggestion",
    title: "Jurisprudence pertinente detectee",
    description:
      "Un nouvel arret de la Cour de cassation (C.24.0312.F) pourrait renforcer votre argumentation dans le dossier Janssens.",
    priority: "medium",
    case_name: "Janssens c/ Etat belge",
  },
  {
    id: "pa-4",
    type: "follow_up",
    title: "Relance client -- SA Construct",
    description:
      "Aucune reponse du client depuis 14 jours concernant les documents requis pour la procedure de faillite.",
    priority: "medium",
    case_name: "SA Construct - Faillite",
  },
];

const PLACEHOLDER_INSIGHTS: BrainInsight[] = [
  {
    id: "pi-1",
    severity: "critical",
    title: "Conflit d'interets potentiel",
    description:
      "Le nouveau contact M. Verhoeven est lie a la partie adverse dans le dossier Dupont. Verification recommandee.",
    case_name: "Dupont c/ Immobel SA",
  },
  {
    id: "pi-2",
    severity: "high",
    title: "Surcharge la semaine prochaine",
    description:
      "7 echeances concentrees entre le 24 et le 28 fevrier. Envisagez de deleguer ou reporter certaines taches.",
  },
  {
    id: "pi-3",
    severity: "medium",
    title: "Honoraires impayees -- 3 dossiers",
    description:
      "Les factures des dossiers Lambert, Peeters et SA Construct sont en retard de plus de 30 jours.",
  },
  {
    id: "pi-4",
    severity: "low",
    title: "Taux de reussite en hausse",
    description:
      "Votre taux de reussite est passe de 72% a 81% ce trimestre. La specialisation en droit commercial semble porter ses fruits.",
  },
];

const PLACEHOLDER_WORKLOAD: WorkloadWeek[] = [
  { week_label: "17-21 fev", deadline_count: 4, capacity: 5 },
  { week_label: "24-28 fev", deadline_count: 7, capacity: 5 },
  { week_label: "3-7 mar", deadline_count: 3, capacity: 5 },
  { week_label: "10-14 mar", deadline_count: 2, capacity: 5 },
];

/* ─────────────────────────── Helpers ─────────────────────────── */

const urgencyConfig: Record<
  string,
  { label: string; variant: "danger" | "warning" | "accent" | "default" }
> = {
  critical: { label: "Critique", variant: "danger" },
  urgent: { label: "Urgent", variant: "warning" },
  attention: { label: "Attention", variant: "accent" },
  normal: { label: "Normal", variant: "default" },
};

const severityConfig: Record<
  string,
  { dotColor: string; variant: "danger" | "warning" | "accent" | "default" }
> = {
  critical: { dotColor: "bg-danger-500", variant: "danger" },
  high: { dotColor: "bg-warning-500", variant: "warning" },
  medium: { dotColor: "bg-yellow-500", variant: "accent" },
  low: { dotColor: "bg-accent-500", variant: "default" },
};

const priorityVariant: Record<
  string,
  "danger" | "warning" | "accent" | "default"
> = {
  critical: "danger",
  high: "warning",
  medium: "accent",
  low: "default",
};

const actionTypeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  alert: AlertTriangle,
  draft: FileEdit,
  suggestion: Lightbulb,
  follow_up: MessageSquare,
};

const sourceIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  email: Mail,
  phone: Phone,
  document: FileCheck,
};

function getHealthColor(score: number): string {
  if (score >= 80) return "bg-success-500";
  if (score >= 60) return "bg-yellow-500";
  if (score >= 40) return "bg-warning-500";
  return "bg-danger-500";
}

function getHealthDotColor(score?: number): string {
  if (score === undefined || score === null) return "bg-neutral-300";
  if (score >= 80) return "bg-success-500";
  if (score >= 60) return "bg-yellow-500";
  if (score >= 40) return "bg-warning-500";
  return "bg-danger-500";
}

function getStatusVariant(
  status: string
): "default" | "success" | "warning" | "danger" | "accent" | "neutral" {
  const s = status.toLowerCase();
  if (s.includes("closed") || s.includes("resolu")) return "success";
  if (s.includes("pending") || s.includes("en attente")) return "warning";
  if (s.includes("urgent") || s.includes("critical")) return "danger";
  return "accent";
}

function getTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 60) return `Il y a ${diffMins}min`;
  if (diffHours < 24) return `Il y a ${diffHours}h`;
  if (diffDays === 1) return "Hier";
  return `Il y a ${diffDays}j`;
}

/* ─────────────────────────── Component ─────────────────────────── */

export default function DashboardPage() {
  const { accessToken, tenantId, email } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Brain data
  const [brainData, setBrainData] = useState<BrainSummaryResponse>(FALLBACK_BRAIN);
  const [usePlaceholders, setUsePlaceholders] = useState(false);

  // Existing data
  const [recentCases, setRecentCases] = useState<RecentCase[]>([]);
  const [inboxItems, setInboxItems] = useState<InboxItem[]>([]);
  const [dashboardStats, setDashboardStats] = useState<DashboardResponse["stats"] | null>(null);

  // Local state for insights (for dismiss)
  const [insights, setInsights] = useState<BrainInsight[]>([]);
  // Local state for actions (for approve/reject/defer)
  const [actions, setActions] = useState<BrainAction[]>([]);

  const fetchData = useCallback(async () => {
    if (!accessToken) return;
    try {
      setLoading(true);
      setError(null);

      const [brainRes, statsRes, recentRes, inboxRes] = await Promise.all([
        apiFetch<BrainSummaryResponse>("/brain/summary", accessToken, {
          tenantId,
        }).catch(() => {
          setUsePlaceholders(true);
          return FALLBACK_BRAIN;
        }),
        apiFetch<DashboardResponse>("/dashboard/stats", accessToken, {
          tenantId,
        }).catch(() => ({})),
        apiFetch<{ items: RecentCase[] }>(
          "/cases?page=1&per_page=5&sort=-updated_at",
          accessToken,
          { tenantId }
        ).catch(() => ({ items: [] })),
        apiFetch<{ items: InboxItem[] }>(
          "/inbox?status=DRAFT&per_page=5",
          accessToken,
          { tenantId }
        ).catch(() => ({ items: [] })),
      ]);

      setBrainData(brainRes);

      // Determine deadlines, actions, insights - use API data or placeholders
      const isBrainEmpty =
        brainRes.critical_deadlines.length === 0 &&
        brainRes.pending_actions.length === 0 &&
        brainRes.recent_insights.length === 0;

      if (isBrainEmpty) {
        setUsePlaceholders(true);
      }

      setInsights(
        brainRes.recent_insights.length > 0
          ? brainRes.recent_insights
          : PLACEHOLDER_INSIGHTS
      );
      setActions(
        brainRes.pending_actions.length > 0
          ? brainRes.pending_actions
          : PLACEHOLDER_ACTIONS
      );

      setDashboardStats(
        "stats" in statsRes && (statsRes as DashboardResponse).stats
          ? (statsRes as DashboardResponse).stats
          : {
              total_cases: 0,
              total_contacts: 0,
              monthly_hours: 0,
              total_invoices: 0,
              total_documents: 0,
              pending_inbox: 0,
            }
      );
      setRecentCases(recentRes.items || []);
      setInboxItems(inboxRes.items || []);
    } catch {
      setError("Impossible de charger les donnees du tableau de bord");
    } finally {
      setLoading(false);
    }
  }, [accessToken, tenantId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* ── Action feedback handler ── */
  const handleActionFeedback = async (
    actionId: string,
    feedback: "approved" | "rejected" | "deferred"
  ) => {
    if (!accessToken) return;
    try {
      await apiFetch(`/brain/actions/${actionId}/feedback`, accessToken, {
        tenantId,
        method: "POST",
        body: JSON.stringify({ action_id: actionId, feedback }),
      });
    } catch {
      // Silently handle - remove from UI regardless
    }
    setActions((prev) => prev.filter((a) => a.id !== actionId));
  };

  /* ── Insight dismiss handler ── */
  const handleDismissInsight = async (insightId: string) => {
    if (!accessToken) return;
    try {
      await apiFetch(`/brain/insights/${insightId}/dismiss`, accessToken, {
        tenantId,
        method: "POST",
        body: JSON.stringify({ insight_id: insightId }),
      });
    } catch {
      // Silently handle
    }
    setInsights((prev) => prev.filter((i) => i.id !== insightId));
  };

  /* ── Loading / Error states ── */
  if (loading) {
    return (
      <div className="p-6">
        <LoadingSkeleton variant="stats" />
        <div className="mt-8">
          <LoadingSkeleton variant="card" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-24">
        <ErrorState message={error} onRetry={() => fetchData()} />
      </div>
    );
  }

  /* ── Computed values ── */
  const displayEmail = email || "Utilisateur";
  const firstName = displayEmail.split("@")[0].split(".")[0];
  const displayName = firstName.charAt(0).toUpperCase() + firstName.slice(1);

  const now = new Date();
  const dateStr = now.toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const deadlines =
    brainData.critical_deadlines.length > 0
      ? brainData.critical_deadlines
      : PLACEHOLDER_DEADLINES;

  const workload =
    brainData.workload_next_weeks.length > 0
      ? brainData.workload_next_weeks
      : PLACEHOLDER_WORKLOAD;

  const totalActiveCases =
    brainData.total_active_cases || dashboardStats?.total_cases || 0;
  const pendingActionsCount = actions.length;
  const criticalDeadlinesCount = deadlines.filter(
    (d) => d.days_remaining <= 7
  ).length;
  const healthScore =
    brainData.health_score ||
    (usePlaceholders ? 74 : 0);

  const riskCases =
    (brainData.risk_distribution.high || 0) +
    (brainData.risk_distribution.critical || 0) ||
    (usePlaceholders ? 3 : 0);

  const maxWorkload = Math.max(
    ...workload.map((w) => Math.max(w.deadline_count, w.capacity)),
    1
  );

  /* ── Render ── */
  return (
    <div>
      {/* ═══════════════════ Section 1: Welcome Header ═══════════════════ */}
      <div className="flex items-center justify-between mb-6 animate-fade">
        <div>
          <h1 className="heading-page">Bonjour, {displayName}</h1>
          <p className="label-overline mt-1.5 capitalize">{dateStr}</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-6 mr-4 text-sm text-[rgb(var(--color-text-secondary))]">
            <span>
              <span className="font-bold text-[rgb(var(--color-text-primary))]">{totalActiveCases}</span>{" "}
              dossiers actifs
            </span>
            <span className="text-[rgb(var(--color-border))]">|</span>
            <span>
              <span className="font-bold text-[rgb(var(--color-text-primary))]">{pendingActionsCount}</span>{" "}
              actions en attente
            </span>
            <span className="text-[rgb(var(--color-border))]">|</span>
            <span>
              <span className={`font-bold ${criticalDeadlinesCount > 0 ? "text-danger-700" : "text-[rgb(var(--color-text-primary))]"}`}>
                {criticalDeadlinesCount}
              </span>{" "}
              écheances critiques
            </span>
          </div>
        </div>
      </div>

      {/* ═══════════════════ Section 2: Brain Intelligence Bar ═══════════════════ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 animate-fade">
        <div className="bg-white rounded-sm relative overflow-hidden p-5" style={{ boxShadow: "var(--shadow-card)" }}>
          <div className="absolute left-0 inset-y-0 w-[3px] bg-danger-600" />
          <div className="flex items-center justify-between mb-3 pl-2">
            <span className="label-overline">Dossiers à risque</span>
            <ShieldAlert className="w-4 h-4 text-danger-600" />
          </div>
          <div className="pl-2">
            <p className="leading-none tracking-tight text-[rgb(var(--color-text-primary))]" style={{ fontFamily: "var(--font-display)", fontSize: "1.875rem", fontWeight: 700 }}>{riskCases}</p>
            {riskCases > 0 && (
              <p className="text-xs text-danger-700 font-semibold mt-2 uppercase tracking-wide">
                {brainData.risk_distribution.critical || (usePlaceholders ? 1 : 0)} critique(s) — action requise
              </p>
            )}
          </div>
        </div>

        <div className="bg-white rounded-sm relative overflow-hidden p-5" style={{ boxShadow: "var(--shadow-card)" }}>
          <div className="absolute left-0 inset-y-0 w-[3px] bg-warning-600" />
          <div className="flex items-center justify-between mb-3 pl-2">
            <span className="label-overline">Échéances critiques</span>
            <Clock className="w-4 h-4 text-warning-600" />
          </div>
          <div className="pl-2">
            <p className="leading-none tracking-tight text-[rgb(var(--color-text-primary))]" style={{ fontFamily: "var(--font-display)", fontSize: "1.875rem", fontWeight: 700 }}>{criticalDeadlinesCount}</p>
            <p className="text-xs text-warning-700 font-semibold mt-2 uppercase tracking-wide">sous 7 jours</p>
          </div>
        </div>

        <div className="bg-white rounded-sm relative overflow-hidden p-5" style={{ boxShadow: "var(--shadow-card)" }}>
          <div className="absolute left-0 inset-y-0 w-[3px] bg-accent" />
          <div className="flex items-center justify-between mb-3 pl-2">
            <span className="label-overline">Actions IA en attente</span>
            <Brain className="w-4 h-4 text-accent-600" />
          </div>
          <div className="pl-2">
            <p className="leading-none tracking-tight text-[rgb(var(--color-text-primary))]" style={{ fontFamily: "var(--font-display)", fontSize: "1.875rem", fontWeight: 700 }}>{pendingActionsCount}</p>
            <p className="text-xs text-accent-700 font-semibold mt-2 uppercase tracking-wide">à traiter</p>
          </div>
        </div>

        <div className="bg-white rounded-sm relative overflow-hidden p-5" style={{ boxShadow: "var(--shadow-card)" }}>
          <div className="absolute left-0 inset-y-0 w-[3px] bg-success-600" />
          <div className="flex items-center justify-between mb-3 pl-2">
            <span className="label-overline">Santé globale</span>
            <Activity className="w-4 h-4 text-success-600" />
          </div>
          <div className="pl-2">
            <div className="flex items-end gap-2">
              <p className="leading-none tracking-tight text-[rgb(var(--color-text-primary))]" style={{ fontFamily: "var(--font-display)", fontSize: "1.875rem", fontWeight: 700 }}>{healthScore}</p>
              <span className="text-sm text-[rgb(var(--color-text-secondary))] pb-0.5">/100</span>
            </div>
            <div className="mt-2.5 w-full bg-[rgb(var(--color-surface-raised))] rounded-full h-1.5">
              <div className={`h-1.5 rounded-full transition-all duration-500 ${getHealthColor(healthScore)}`} style={{ width: `${Math.min(healthScore, 100)}%` }} />
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════════════ Section 3: Two-Column Layout ═══════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-6">
        {/* ── Left Column (3/5 = ~60%) ── */}
        <div className="lg:col-span-3 space-y-6">
          {/* Prochaines echeances */}
          <Card
            className="animate-fade"
            variant="accent-top"
            header={
              <div className="flex items-center justify-between">
                <h3 className="heading-section">Prochaines échéances</h3>
                <Badge variant="default" size="sm">{deadlines.length} total</Badge>
              </div>
            }
            footer={undefined}
          >
            {deadlines.length === 0 ? (
              <EmptyState
                title="Aucune échéance"
                description="Pas d'échéances à venir"
                icon={<CalendarDays className="h-12 w-12 text-neutral-300" />}
              />
            ) : (
              <div className="-mx-6 -mb-6">
                {deadlines.map((deadline) => {
                  const isCritical = deadline.urgency === "critical";
                  const isUrgent = deadline.urgency === "urgent";
                  const dayColor = isCritical
                    ? "text-danger-700"
                    : isUrgent
                    ? "text-warning-700"
                    : "text-[rgb(var(--color-text-secondary))]";
                  return (
                    <div
                      key={deadline.id}
                      className={`flex items-center gap-0 border-b border-[rgb(var(--color-border))]/50 last:border-0 transition-colors duration-100 cursor-pointer group ${
                        isCritical
                          ? "bg-danger-50/60 hover:bg-danger-50"
                          : "hover:bg-[rgb(var(--color-surface-raised))]"
                      }`}
                    >
                      {/* Date column */}
                      <div className="w-16 flex-shrink-0 text-center py-3 px-2">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-[rgb(var(--color-text-secondary))]">
                          {new Date(deadline.due_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" })}
                        </p>
                        <p className={`font-bold leading-none mt-0.5 ${dayColor} ${isCritical ? "animate-critical" : ""}`}
                           style={{ fontFamily: "var(--font-display)", fontSize: "1.25rem" }}>
                          {deadline.days_remaining}j
                        </p>
                      </div>

                      {/* Vertical divider */}
                      <div className={`w-px self-stretch flex-shrink-0 ${isCritical ? "bg-danger-200" : "bg-[rgb(var(--color-border))]/50"}`} />

                      {/* Content */}
                      <div className="flex-1 min-w-0 py-3 px-4">
                        <p className="text-sm font-semibold text-[rgb(var(--color-text-primary))] truncate group-hover:text-accent transition-colors duration-100">
                          {deadline.title}
                        </p>
                        <p className="text-xs text-[rgb(var(--color-text-secondary))] truncate mt-0.5">
                          {deadline.case_name}
                        </p>
                      </div>

                      {/* Badge — only for critical/urgent */}
                      {(isCritical || isUrgent) && (
                        <div className="pr-4 flex-shrink-0">
                          <Badge variant={isCritical ? "danger" : "warning"} filled={isCritical} size="sm">
                            {isCritical ? "Critique" : "Urgent"}
                          </Badge>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Actions intelligentes */}
          <Card
            className="animate-fade"
            header={
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Brain className="w-4 h-4 text-accent-600" />
                  <h3 className="heading-section">Actions intelligentes</h3>
                </div>
                <Badge variant="accent" size="sm">{actions.length} en attente</Badge>
              </div>
            }
          >
            {actions.length === 0 ? (
              <EmptyState
                title="Aucune action en attente"
                description="L'IA n'a aucune suggestion pour le moment"
                icon={<Brain className="h-12 w-12 text-neutral-300" />}
              />
            ) : (
              <div className="space-y-3">
                {actions.map((action) => {
                  const ActionIcon =
                    actionTypeIcons[action.type] || Lightbulb;
                  const pVariant =
                    priorityVariant[action.priority] || "default";
                  return (
                    <div
                      key={action.id}
                      className="p-4 border border-neutral-200 rounded hover:shadow-sm transition-shadow duration-150"
                    >
                      <div className="flex items-start gap-3">
                        <div
                          className={`p-2 rounded flex-shrink-0 mt-0.5 ${
                            action.priority === "critical"
                              ? "bg-danger-100"
                              : action.priority === "high"
                                ? "bg-warning-100"
                                : "bg-accent-100"
                          }`}
                        >
                          <ActionIcon
                            className={`w-4 h-4 ${
                              action.priority === "critical"
                                ? "text-danger-600"
                                : action.priority === "high"
                                  ? "text-warning-600"
                                  : "text-accent-600"
                            }`}
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <p className="text-sm font-semibold text-neutral-900">
                              {action.title}
                            </p>
                            <Badge variant={pVariant} size="sm">
                              {action.priority}
                            </Badge>
                          </div>
                          <p className="text-xs text-neutral-600 mb-2 leading-relaxed">
                            {action.description}
                          </p>
                          {action.case_name && (
                            <p className="text-xs text-neutral-400 mb-3">
                              Dossier : {action.case_name}
                            </p>
                          )}
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() =>
                                handleActionFeedback(action.id, "approved")
                              }
                              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-success-100 text-success-700 rounded hover:bg-success-200 transition-colors duration-150"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Approuver
                            </button>
                            <button
                              onClick={() =>
                                handleActionFeedback(action.id, "rejected")
                              }
                              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-danger-100 text-danger-700 rounded hover:bg-danger-200 transition-colors duration-150"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                              Rejeter
                            </button>
                            <button
                              onClick={() =>
                                handleActionFeedback(action.id, "deferred")
                              }
                              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-neutral-100 text-neutral-700 rounded hover:bg-neutral-200 transition-colors duration-150"
                            >
                              <Timer className="w-3.5 h-3.5" />
                              Reporter
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>

        {/* ── Right Column (2/5 = ~40%) ── */}
        <div className="lg:col-span-2 space-y-6">
          {/* Insights IA */}
          <Card
            className="animate-fade"
            header={
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-accent-600" />
                  <h3 className="heading-section">Insights IA</h3>
                </div>
                <Badge variant="accent" size="sm">{insights.length}</Badge>
              </div>
            }
          >
            {insights.length === 0 ? (
              <EmptyState
                title="Aucun insight"
                description="Rien à signaler pour le moment"
                icon={<Lightbulb className="h-12 w-12 text-neutral-300" />}
              />
            ) : (
              <div className="space-y-3">
                {insights.map((insight) => {
                  const isCritical = insight.severity === "critical";
                  const severityBarClass =
                    isCritical ? "bg-danger-600 w-full animate-critical" :
                    insight.severity === "high" ? "bg-warning-600 w-3/4" :
                    insight.severity === "medium" ? "bg-yellow-500 w-1/2" :
                    "bg-neutral-200 w-1/4";
                  return (
                    <div
                      key={insight.id}
                      className="group relative p-3 border border-[rgb(var(--color-border))]/60 rounded-sm hover:border-[rgb(var(--color-border))] transition-colors duration-150"
                    >
                      {/* Severity bar */}
                      <div className={`h-[2px] rounded-full mb-2.5 transition-all ${severityBarClass}`} />

                      <button
                        onClick={() => handleDismissInsight(insight.id)}
                        className="absolute top-3 right-2 p-1 rounded-sm opacity-0 group-hover:opacity-100 hover:bg-[rgb(var(--color-surface-raised))] transition-all duration-150"
                        title="Masquer"
                      >
                        <X className="w-3.5 h-3.5 text-[rgb(var(--color-text-secondary))]" />
                      </button>
                      <div className="pr-6">
                        <p className="text-sm font-semibold text-[rgb(var(--color-text-primary))] mb-0.5">
                          {insight.title}
                        </p>
                        <p className="text-xs text-[rgb(var(--color-text-secondary))] leading-relaxed">
                          {insight.description}
                        </p>
                        {insight.case_name && (
                          <p className="text-xs text-accent-600 mt-1.5 flex items-center gap-1 cursor-pointer hover:text-accent-700">
                            <ChevronRight className="w-3 h-3" />
                            {insight.case_name}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Dossiers recents */}
          <Card
            className="animate-fade"
            header={<h3 className="heading-section">Dossiers récents</h3>}
          >
            {recentCases.length === 0 ? (
              <EmptyState
                title="Aucun dossier récent"
                description="Vos dossiers apparaîtront ici"
                icon={<FolderOpen className="h-12 w-12 text-neutral-300" />}
              />
            ) : (
              <div className="space-y-1">
                {recentCases.slice(0, 5).map((caseItem) => (
                  <div
                    key={caseItem.id}
                    className="flex items-center gap-3 py-2.5 px-2 rounded-sm hover:bg-[rgb(var(--color-surface-raised))] transition-colors duration-100 cursor-pointer group"
                  >
                    <span
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${getHealthDotColor(caseItem.health_score)}`}
                      title={caseItem.health_score !== undefined ? `Santé: ${caseItem.health_score}/100` : "Santé non évaluée"}
                    />
                    <Badge variant={getStatusVariant(caseItem.status)} size="sm">
                      {caseItem.status}
                    </Badge>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm text-[rgb(var(--color-text-primary))] group-hover:text-accent transition-colors duration-100 truncate">
                        {caseItem.title}
                      </p>
                      <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-0.5">
                        {getTimeAgo(caseItem.updated_at)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Inbox a traiter */}
          <Card
            className="animate-fade"
            header={
              <div className="flex items-center justify-between">
                <h3 className="heading-section">Inbox à traiter</h3>
                {inboxItems.length > 0 && (
                  <Badge variant="warning" filled size="sm">{inboxItems.length}</Badge>
                )}
              </div>
            }
          >
            {inboxItems.length === 0 ? (
              <EmptyState
                title="Aucun élément en attente"
                description="Votre inbox est vide"
                icon={<InboxIcon className="h-12 w-12 text-neutral-300" />}
              />
            ) : (
              <div className="space-y-1">
                {inboxItems.slice(0, 5).map((item) => {
                  const SourceIcon = sourceIcons[item.source] || Mail;
                  return (
                    <div
                      key={item.id}
                      className="flex items-center gap-3 py-2.5 px-2 rounded-sm hover:bg-[rgb(var(--color-surface-raised))] transition-colors duration-100 cursor-pointer group"
                    >
                      <SourceIcon className="w-4 h-4 text-[rgb(var(--color-text-secondary))] flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-[rgb(var(--color-text-primary))] group-hover:text-accent truncate transition-colors duration-100">
                          {item.subject || "(Sans titre)"}
                        </p>
                        {item.from_name && (
                          <p className="text-xs text-[rgb(var(--color-text-secondary))] truncate">
                            {item.from_name}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* ═══════════════════ Section 4: Full Width - Workload Chart ═══════════════════ */}
      <Card
        className="animate-fade mb-6"
        header={
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-primary" />
              <h3 className="font-display text-lg font-semibold text-neutral-900">
                Charge de travail -- 4 prochaines semaines
              </h3>
            </div>
            <div className="flex items-center gap-4 text-xs text-neutral-500">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 bg-accent-500 rounded-sm" />
                Echeances
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 bg-neutral-200 rounded-sm border border-dashed border-neutral-400" />
                Capacite
              </span>
            </div>
          </div>
        }
      >
        <div className="space-y-4">
          {workload.map((week, index) => {
            const isOverloaded = week.deadline_count > week.capacity;
            const barWidth = Math.max(
              (week.deadline_count / maxWorkload) * 100,
              4
            );
            const capacityWidth = (week.capacity / maxWorkload) * 100;
            return (
              <div key={index} className="flex items-center gap-4">
                <div className="w-24 flex-shrink-0 text-right">
                  <span className="text-sm font-medium text-neutral-700">
                    {week.week_label}
                  </span>
                </div>
                <div className="flex-1 relative">
                  {/* Capacity marker */}
                  <div
                    className="absolute top-0 h-full border-r-2 border-dashed border-neutral-300 z-10"
                    style={{ left: `${capacityWidth}%` }}
                  />
                  {/* Bar background */}
                  <div className="w-full bg-neutral-100 rounded h-8 relative overflow-hidden">
                    <div
                      className={`h-full rounded transition-all duration-500 ${
                        isOverloaded
                          ? "bg-danger-500"
                          : "bg-accent-500"
                      }`}
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                </div>
                <div className="w-16 flex-shrink-0">
                  <span
                    className={`text-sm font-bold ${
                      isOverloaded ? "text-danger-600" : "text-neutral-700"
                    }`}
                  >
                    {week.deadline_count}
                  </span>
                  <span className="text-xs text-neutral-400">
                    /{week.capacity}
                  </span>
                </div>
                {isOverloaded && (
                  <Badge variant="danger" size="sm">
                    surcharge
                  </Badge>
                )}
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
