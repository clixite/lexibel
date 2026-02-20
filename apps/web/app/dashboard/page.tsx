"use client";

import { useAuth } from "@/lib/useAuth";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
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
  DollarSign,
  Receipt,
  Percent,
  FileText,
  MapPin,
  Plus,
  UserPlus,
  ScanLine,
  CircleDollarSign,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
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

interface BillingReportResponse {
  total_unbilled_hours: number;
  total_unbilled_amount: number;
  recovery_rate: number;
  anomalies: unknown[];
  invoice_suggestions: unknown[];
  recommendations: unknown[];
}

interface CalendarEvent {
  id: string;
  title: string;
  start_time: string;
  end_time?: string;
  location?: string;
}

interface BillingAlert {
  id: string;
  message: string;
  severity: "warning" | "danger";
}

interface RevenueTrendPoint {
  month: string;
  facture: number;
  encaisse: number;
}

interface CaseDistributionSlice {
  name: string;
  value: number;
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

const FALLBACK_BILLING: BillingReportResponse = {
  total_unbilled_hours: 0,
  total_unbilled_amount: 0,
  recovery_rate: 0,
  anomalies: [],
  invoice_suggestions: [],
  recommendations: [],
};

const PIE_COLORS = [
  "#6366f1", // accent-500
  "#22c55e", // success-500
  "#f59e0b", // warning-500
  "#a3a3a3", // neutral-400
  "#ef4444", // danger-500
  "#06b6d4", // cyan-500
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
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Brain data
  const [brainData, setBrainData] = useState<BrainSummaryResponse>(FALLBACK_BRAIN);

  // Existing data
  const [recentCases, setRecentCases] = useState<RecentCase[]>([]);
  const [inboxItems, setInboxItems] = useState<InboxItem[]>([]);
  const [dashboardStats, setDashboardStats] = useState<DashboardResponse["stats"] | null>(null);

  // Local state for insights (for dismiss)
  const [insights, setInsights] = useState<BrainInsight[]>([]);
  // Local state for actions (for approve/reject/defer)
  const [actions, setActions] = useState<BrainAction[]>([]);

  // New: Billing report data
  const [billingReport, setBillingReport] = useState<BillingReportResponse>(FALLBACK_BILLING);
  // New: Today's calendar events
  const [todayEvents, setTodayEvents] = useState<CalendarEvent[]>([]);
  // Revenue trend & case distribution from API
  const [revenueTrend, setRevenueTrend] = useState<RevenueTrendPoint[]>([]);
  const [caseDistribution, setCaseDistribution] = useState<CaseDistributionSlice[]>([]);
  // Billing alerts from API
  const [billingAlerts, setBillingAlerts] = useState<BillingAlert[]>([]);

  const fetchData = useCallback(async () => {
    if (!accessToken) return;
    try {
      setLoading(true);
      setError(null);

      // Build date range for today's calendar events
      const todayStart = new Date();
      todayStart.setHours(0, 0, 0, 0);
      const tomorrowStart = new Date(todayStart);
      tomorrowStart.setDate(tomorrowStart.getDate() + 1);
      const afterParam = todayStart.toISOString().split("T")[0];
      const beforeParam = tomorrowStart.toISOString().split("T")[0];

      const [brainRes, statsRes, recentRes, inboxRes, billingRes, calendarRes, revenueTrendRes, caseDistRes, billingAlertsRes] = await Promise.all([
        apiFetch<BrainSummaryResponse>("/brain/summary", accessToken, {
          tenantId,
        }).catch(() => FALLBACK_BRAIN),
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
        apiFetch<BillingReportResponse>("/brain/billing/report", accessToken, {
          tenantId,
        }).catch(() => FALLBACK_BILLING),
        apiFetch<{ items: CalendarEvent[] }>(
          `/calendar/events?after=${afterParam}&before=${beforeParam}`,
          accessToken,
          { tenantId }
        ).catch(() => ({ items: [] })),
        apiFetch<{ items: RevenueTrendPoint[] }>("/dashboard/stats/revenue-trend", accessToken, {
          tenantId,
        }).catch(() => ({ items: [] })),
        apiFetch<{ items: CaseDistributionSlice[] }>("/dashboard/stats/case-distribution", accessToken, {
          tenantId,
        }).catch(() => ({ items: [] })),
        apiFetch<{ items: BillingAlert[] }>("/brain/billing/alerts", accessToken, {
          tenantId,
        }).catch(() => ({ items: [] })),
      ]);

      setBrainData(brainRes);

      setInsights(brainRes.recent_insights);
      setActions(brainRes.pending_actions);

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
      setBillingReport(billingRes);
      setTodayEvents(calendarRes.items || []);
      setRevenueTrend(revenueTrendRes.items || []);
      setCaseDistribution(caseDistRes.items || []);
      setBillingAlerts(billingAlertsRes.items || []);
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
      <div className="min-h-screen bg-neutral-50 p-6">
        <LoadingSkeleton variant="stats" />
        <div className="mt-8">
          <LoadingSkeleton variant="card" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
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

  const deadlines = brainData.critical_deadlines;

  const workload = brainData.workload_next_weeks;

  const totalActiveCases =
    brainData.total_active_cases || dashboardStats?.total_cases || 0;
  const pendingActionsCount = actions.length;
  const criticalDeadlinesCount = deadlines.filter(
    (d) => d.days_remaining <= 7
  ).length;
  const healthScore = brainData.health_score || 0;

  const riskCases =
    (brainData.risk_distribution.high || 0) +
    (brainData.risk_distribution.critical || 0);

  const maxWorkload = Math.max(
    ...workload.map((w) => Math.max(w.deadline_count, w.capacity)),
    1
  );

  /* ── Render ── */
  return (
    <div className="min-h-screen bg-neutral-50">
      {/* ═══════════════════ Section 1: Welcome Header ═══════════════════ */}
      <div className="mb-6 animate-fade">
        <div className="relative overflow-hidden bg-white border border-neutral-200 p-8 md:p-10">
          <div className="relative z-10">
            <h1 className="text-3xl md:text-4xl font-display font-bold text-primary mb-2">
              Bonjour, {displayName}
            </h1>
            <p className="text-base text-neutral-600 capitalize mb-3">
              {dateStr}
            </p>
            <p className="text-sm text-neutral-500">
              <span className="font-medium text-neutral-700">
                {totalActiveCases}
              </span>{" "}
              dossiers actifs
              <span className="mx-2 text-neutral-300">|</span>
              <span className="font-medium text-neutral-700">
                {pendingActionsCount}
              </span>{" "}
              actions en attente
              <span className="mx-2 text-neutral-300">|</span>
              <span className="font-medium text-neutral-700">
                {criticalDeadlinesCount}
              </span>{" "}
              echeances cette semaine
            </p>
          </div>
        </div>
      </div>

      {/* ═══════════════════ Section 2: Brain Intelligence Bar ═══════════════════ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 animate-fade">
        {/* Dossiers a risque */}
        <div className="bg-white rounded shadow-sm p-5 border-l-4 border-danger-500">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
              Dossiers a risque
            </h3>
            <div className="p-1.5 bg-danger-100 rounded">
              <ShieldAlert className="w-4 h-4 text-danger-600" />
            </div>
          </div>
          <div className="flex items-end gap-3">
            <p className="text-3xl font-bold text-neutral-900">{riskCases}</p>
            {/* Mini sparkline - simple visual */}
            <div className="flex items-end gap-0.5 pb-1">
              {[3, 5, 4, 6, 3, 7, riskCases].map((v, i) => (
                <div
                  key={i}
                  className={`w-1 rounded-sm ${
                    i === 6 ? "bg-danger-500" : "bg-danger-200"
                  }`}
                  style={{ height: `${Math.max(4, (v / 8) * 20)}px` }}
                />
              ))}
            </div>
          </div>
          {riskCases > 0 && (
            <p className="text-xs text-danger-600 mt-2 font-medium">
              {brainData.risk_distribution.critical || 0}{" "}
              critique(s)
            </p>
          )}
        </div>

        {/* Echeances critiques */}
        <div className="bg-white rounded shadow-sm p-5 border-l-4 border-warning-500">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
              Echeances critiques
            </h3>
            <div className="p-1.5 bg-warning-100 rounded">
              <Clock className="w-4 h-4 text-warning-600" />
            </div>
          </div>
          <p className="text-3xl font-bold text-neutral-900">
            {criticalDeadlinesCount}
          </p>
          <p className="text-xs text-warning-600 mt-2 font-medium">
            sous 7 jours
          </p>
        </div>

        {/* Actions IA en attente */}
        <div className="bg-white rounded shadow-sm p-5 border-l-4 border-accent-500">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
              Actions IA en attente
            </h3>
            <div className="p-1.5 bg-accent-100 rounded">
              <Brain className="w-4 h-4 text-accent-600" />
            </div>
          </div>
          <p className="text-3xl font-bold text-neutral-900">
            {pendingActionsCount}
          </p>
          <p className="text-xs text-accent-600 mt-2 font-medium">
            a traiter
          </p>
        </div>

        {/* Score de sante global */}
        <div className="bg-white rounded shadow-sm p-5 border-l-4 border-success-500">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
              Sante globale
            </h3>
            <div className="p-1.5 bg-success-100 rounded">
              <Activity className="w-4 h-4 text-success-600" />
            </div>
          </div>
          <div className="flex items-end gap-3">
            <p className="text-3xl font-bold text-neutral-900">
              {healthScore}
            </p>
            <span className="text-sm text-neutral-500 pb-1">/100</span>
          </div>
          {/* Gauge bar */}
          <div className="mt-2 w-full bg-neutral-100 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${getHealthColor(healthScore)}`}
              style={{ width: `${Math.min(healthScore, 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* ═══════════════════ Section 2b: Financial KPI Row ═══════════════════ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 animate-fade">
        {/* Heures du mois */}
        <div className="bg-white rounded shadow-sm p-5 border-l-4 border-accent-500">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
              Heures du mois
            </h3>
            <div className="p-1.5 bg-accent-100 rounded">
              <Clock className="w-4 h-4 text-accent-600" />
            </div>
          </div>
          <div className="flex items-end gap-2">
            <p className="text-3xl font-bold text-neutral-900">
              {dashboardStats?.monthly_hours?.toFixed(1) || "0.0"}h
            </p>
            <TrendingUp className="w-4 h-4 text-success-500 mb-1" />
          </div>
          <p className="text-xs text-neutral-500 mt-2">
            ce mois
          </p>
        </div>

        {/* A facturer */}
        <div className="bg-white rounded shadow-sm p-5 border-l-4 border-warning-500">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
              A facturer
            </h3>
            <div className="p-1.5 bg-warning-100 rounded">
              <CircleDollarSign className="w-4 h-4 text-warning-600" />
            </div>
          </div>
          <p className="text-3xl font-bold text-neutral-900">
            {new Intl.NumberFormat("fr-BE", {
              style: "currency",
              currency: "EUR",
              minimumFractionDigits: 0,
              maximumFractionDigits: 0,
            }).format(billingReport.total_unbilled_amount)}
          </p>
          <p className="text-xs text-neutral-500 mt-2">
            {billingReport.total_unbilled_hours.toFixed(1)}h non facturees
          </p>
        </div>

        {/* Taux recouvrement */}
        <div className="bg-white rounded shadow-sm p-5 border-l-4 border-success-500">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
              Taux recouvrement
            </h3>
            <div className="p-1.5 bg-success-100 rounded">
              <Percent className="w-4 h-4 text-success-600" />
            </div>
          </div>
          <p
            className={`text-3xl font-bold ${
              billingReport.recovery_rate >= 0.8
                ? "text-success-600"
                : billingReport.recovery_rate >= 0.6
                  ? "text-warning-600"
                  : "text-danger-600"
            }`}
          >
            {Math.round(billingReport.recovery_rate * 100)}%
          </p>
          <div className="mt-2 w-full bg-neutral-100 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${
                billingReport.recovery_rate >= 0.8
                  ? "bg-success-500"
                  : billingReport.recovery_rate >= 0.6
                    ? "bg-warning-500"
                    : "bg-danger-500"
              }`}
              style={{
                width: `${Math.min(billingReport.recovery_rate * 100, 100)}%`,
              }}
            />
          </div>
        </div>

        {/* Factures en attente */}
        <div className="bg-white rounded shadow-sm p-5 border-l-4 border-neutral-400">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
              Factures en attente
            </h3>
            <div className="p-1.5 bg-neutral-100 rounded">
              <Receipt className="w-4 h-4 text-neutral-600" />
            </div>
          </div>
          <p className="text-3xl font-bold text-neutral-900">
            {dashboardStats?.total_invoices || 0}
          </p>
          <p className="text-xs text-neutral-500 mt-2">
            a traiter
          </p>
        </div>
      </div>

      {/* ═══════════════════ Section 2c: Today's Agenda ═══════════════════ */}
      <Card
        className="animate-fade mb-6"
        header={
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CalendarDays className="w-5 h-5 text-accent-600" />
              <h3 className="font-display text-lg font-semibold text-neutral-900">
                Agenda du jour
              </h3>
            </div>
            <button
              onClick={() => router.push("/dashboard/calendar")}
              className="text-xs font-medium text-accent-600 hover:text-accent-700 transition-colors duration-150 flex items-center gap-1"
            >
              Voir le calendrier
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        }
      >
        {todayEvents.length === 0 ? (
          <p className="text-sm text-neutral-500 py-2">
            Aucun rendez-vous aujourd&apos;hui
          </p>
        ) : (
          <div className="flex flex-wrap gap-4">
            {todayEvents.map((event) => (
              <div
                key={event.id}
                className="flex items-center gap-3 p-3 border border-neutral-200 rounded hover:bg-neutral-50 transition-colors duration-150 min-w-[220px] flex-1"
              >
                <div className="p-2 bg-accent-100 rounded flex-shrink-0">
                  <Clock className="w-4 h-4 text-accent-600" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-neutral-900 truncate">
                    {event.title}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-neutral-500">
                      {new Date(event.start_time).toLocaleTimeString("fr-FR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                      {event.end_time &&
                        ` - ${new Date(event.end_time).toLocaleTimeString(
                          "fr-FR",
                          { hour: "2-digit", minute: "2-digit" }
                        )}`}
                    </span>
                    {event.location && (
                      <span className="text-xs text-neutral-400 flex items-center gap-0.5 truncate">
                        <MapPin className="w-3 h-3" />
                        {event.location}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ═══════════════════ Section 2d: Quick Actions Bar ═══════════════════ */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6 animate-fade">
        <button
          onClick={() => router.push("/dashboard/cases/new")}
          className="flex items-center gap-3 bg-white border border-neutral-200 rounded p-4 hover:border-accent-400 hover:bg-accent-50 transition-all duration-150 group"
        >
          <div className="p-2 bg-accent-100 rounded group-hover:bg-accent-200 transition-colors duration-150">
            <Plus className="w-4 h-4 text-accent-600" />
          </div>
          <span className="text-sm font-medium text-neutral-700 group-hover:text-accent-700 transition-colors duration-150">
            Nouveau dossier
          </span>
        </button>

        <button
          onClick={() => router.push("/dashboard/billing")}
          className="flex items-center gap-3 bg-white border border-neutral-200 rounded p-4 hover:border-accent-400 hover:bg-accent-50 transition-all duration-150 group"
        >
          <div className="p-2 bg-success-100 rounded group-hover:bg-success-200 transition-colors duration-150">
            <DollarSign className="w-4 h-4 text-success-600" />
          </div>
          <span className="text-sm font-medium text-neutral-700 group-hover:text-accent-700 transition-colors duration-150">
            Nouvelle prestation
          </span>
        </button>

        <button
          onClick={() => router.push("/dashboard/contacts")}
          className="flex items-center gap-3 bg-white border border-neutral-200 rounded p-4 hover:border-accent-400 hover:bg-accent-50 transition-all duration-150 group"
        >
          <div className="p-2 bg-warning-100 rounded group-hover:bg-warning-200 transition-colors duration-150">
            <UserPlus className="w-4 h-4 text-warning-600" />
          </div>
          <span className="text-sm font-medium text-neutral-700 group-hover:text-accent-700 transition-colors duration-150">
            Nouveau contact
          </span>
        </button>

        <button
          onClick={() => router.push("/dashboard/documents")}
          className="flex items-center gap-3 bg-white border border-neutral-200 rounded p-4 hover:border-accent-400 hover:bg-accent-50 transition-all duration-150 group"
        >
          <div className="p-2 bg-neutral-100 rounded group-hover:bg-neutral-200 transition-colors duration-150">
            <ScanLine className="w-4 h-4 text-neutral-600" />
          </div>
          <span className="text-sm font-medium text-neutral-700 group-hover:text-accent-700 transition-colors duration-150">
            Scanner document
          </span>
        </button>
      </div>

      {/* ═══════════════════ Section 3: Two-Column Layout ═══════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-6">
        {/* ── Left Column (3/5 = ~60%) ── */}
        <div className="lg:col-span-3 space-y-6">
          {/* Evolution du chiffre d'affaires */}
          <Card
            className="animate-fade"
            header={
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-accent-600" />
                  <h3 className="font-display text-lg font-semibold text-neutral-900">
                    Evolution du chiffre d&apos;affaires
                  </h3>
                </div>
                <div className="flex items-center gap-4 text-xs text-neutral-500">
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 bg-accent-500 rounded-sm" />
                    Facture
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 bg-success-500 rounded-sm" />
                    Encaisse
                  </span>
                </div>
              </div>
            }
          >
            {revenueTrend.length === 0 ? (
              <EmptyState
                title="Aucune donnee"
                description="Les donnees de chiffre d'affaires apparaitront ici"
                icon={<TrendingUp className="h-12 w-12 text-neutral-300" />}
              />
            ) : (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={revenueTrend}>
                    <XAxis
                      dataKey="month"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fontSize: 12, fill: "#737373" }}
                    />
                    <YAxis
                      axisLine={false}
                      tickLine={false}
                      tick={{ fontSize: 12, fill: "#737373" }}
                      tickFormatter={(v: number) =>
                        `${(v / 1000).toFixed(0)}k`
                      }
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#fff",
                        border: "1px solid #e5e5e5",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      formatter={(value) => [
                        new Intl.NumberFormat("fr-BE", {
                          style: "currency",
                          currency: "EUR",
                          minimumFractionDigits: 0,
                        }).format(value as number),
                      ]}
                    />
                    <Line
                      type="monotone"
                      dataKey="facture"
                      name="Facture"
                      stroke="#6366f1"
                      strokeWidth={2}
                      dot={{ r: 4, fill: "#6366f1" }}
                      activeDot={{ r: 6 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="encaisse"
                      name="Encaisse"
                      stroke="#22c55e"
                      strokeWidth={2}
                      dot={{ r: 4, fill: "#22c55e" }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </Card>

          {/* Prochaines echeances */}
          <Card
            className="animate-fade"
            header={
              <div className="flex items-center justify-between">
                <h3 className="font-display text-lg font-semibold text-neutral-900">
                  Prochaines echeances
                </h3>
                <Badge variant="default" size="sm">
                  {deadlines.length} total
                </Badge>
              </div>
            }
          >
            {deadlines.length === 0 ? (
              <EmptyState
                title="Aucune echeance"
                description="Pas d'echeances a venir"
                icon={<CalendarDays className="h-12 w-12 text-neutral-300" />}
              />
            ) : (
              <div className="space-y-2">
                {deadlines.map((deadline) => {
                  const config = urgencyConfig[deadline.urgency] || urgencyConfig.normal;
                  return (
                    <div
                      key={deadline.id}
                      className={`flex items-center gap-4 p-3 rounded border transition-colors duration-150 cursor-pointer group ${
                        deadline.urgency === "critical"
                          ? "border-danger-200 bg-danger-50/50 hover:bg-danger-50"
                          : deadline.urgency === "urgent"
                            ? "border-warning-200 bg-warning-50/30 hover:bg-warning-50/50"
                            : "border-neutral-200 hover:bg-neutral-50"
                      }`}
                    >
                      <div
                        className={`p-2 rounded flex-shrink-0 ${
                          deadline.urgency === "critical"
                            ? "bg-danger-100"
                            : deadline.urgency === "urgent"
                              ? "bg-warning-100"
                              : "bg-primary/10"
                        }`}
                      >
                        <CalendarDays
                          className={`w-4 h-4 ${
                            deadline.urgency === "critical"
                              ? "text-danger-600"
                              : deadline.urgency === "urgent"
                                ? "text-warning-600"
                                : "text-primary"
                          }`}
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-neutral-900 group-hover:text-primary transition-colors duration-150 truncate">
                          {deadline.title}
                        </p>
                        <p className="text-xs text-neutral-500 mt-0.5 truncate">
                          {deadline.case_name}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className="text-xs text-neutral-500 hidden sm:inline">
                          {new Date(deadline.due_date).toLocaleDateString(
                            "fr-FR",
                            { day: "numeric", month: "short" }
                          )}
                        </span>
                        <Badge variant={config.variant} size="sm">
                          {deadline.days_remaining}j
                        </Badge>
                      </div>
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
                  <Brain className="w-5 h-5 text-accent-600" />
                  <h3 className="font-display text-lg font-semibold text-neutral-900">
                    Actions intelligentes
                  </h3>
                </div>
                <Badge variant="accent" size="sm">
                  {actions.length} en attente
                </Badge>
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
          {/* Repartition des dossiers */}
          <Card
            className="animate-fade"
            header={
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Briefcase className="w-5 h-5 text-accent-600" />
                  <h3 className="font-display text-lg font-semibold text-neutral-900">
                    Repartition des dossiers
                  </h3>
                </div>
                <Badge variant="default" size="sm">
                  {caseDistribution.reduce((s, c) => s + c.value, 0)} total
                </Badge>
              </div>
            }
          >
            {caseDistribution.length === 0 ? (
              <EmptyState
                title="Aucune donnee"
                description="La repartition des dossiers apparaitra ici"
                icon={<Briefcase className="h-12 w-12 text-neutral-300" />}
              />
            ) : (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={caseDistribution}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      innerRadius={40}
                      paddingAngle={2}
                      dataKey="value"
                      label={({ name, percent }) =>
                        `${name || ""} ${((percent as number) * 100).toFixed(0)}%`
                      }
                      labelLine={{ strokeWidth: 1 }}
                    >
                      {caseDistribution.map((_, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={PIE_COLORS[index % PIE_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#fff",
                        border: "1px solid #e5e5e5",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                      formatter={(value) => [`${value} dossiers`]}
                    />
                    <Legend
                      verticalAlign="bottom"
                      height={36}
                      iconType="circle"
                      iconSize={8}
                      formatter={(value: string) => (
                        <span className="text-xs text-neutral-600">{value}</span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </Card>

          {/* Alertes facturation */}
          <Card
            className="animate-fade"
            header={
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-warning-600" />
                  <h3 className="font-display text-lg font-semibold text-neutral-900">
                    Alertes facturation
                  </h3>
                </div>
                <button
                  onClick={() => router.push("/dashboard/billing")}
                  className="text-xs font-medium text-accent-600 hover:text-accent-700 transition-colors duration-150 flex items-center gap-1"
                >
                  Voir la facturation
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            }
          >
            {billingAlerts.length === 0 ? (
              <EmptyState
                title="Aucune alerte"
                description="Pas d'alertes de facturation pour le moment"
                icon={<AlertTriangle className="h-12 w-12 text-neutral-300" />}
              />
            ) : (
              <div className="space-y-2">
                {billingAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`flex items-start gap-3 p-3 rounded border transition-colors duration-150 ${
                      alert.severity === "danger"
                        ? "border-danger-200 bg-danger-50/50"
                        : "border-warning-200 bg-warning-50/30"
                    }`}
                  >
                    <div
                      className={`p-1.5 rounded flex-shrink-0 mt-0.5 ${
                        alert.severity === "danger"
                          ? "bg-danger-100"
                          : "bg-warning-100"
                      }`}
                    >
                      <AlertTriangle
                        className={`w-3.5 h-3.5 ${
                          alert.severity === "danger"
                            ? "text-danger-600"
                            : "text-warning-600"
                        }`}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-neutral-800 leading-relaxed">
                        {alert.message}
                      </p>
                    </div>
                    <Badge
                      variant={alert.severity === "danger" ? "danger" : "warning"}
                      size="sm"
                    >
                      {alert.severity === "danger" ? "Critique" : "Attention"}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Insights IA */}
          <Card
            className="animate-fade"
            header={
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Lightbulb className="w-5 h-5 text-accent-600" />
                  <h3 className="font-display text-lg font-semibold text-neutral-900">
                    Insights IA
                  </h3>
                </div>
                <Badge variant="accent" size="sm">
                  {insights.length}
                </Badge>
              </div>
            }
          >
            {insights.length === 0 ? (
              <EmptyState
                title="Aucun insight"
                description="Rien a signaler pour le moment"
                icon={<Lightbulb className="h-12 w-12 text-neutral-300" />}
              />
            ) : (
              <div className="space-y-3">
                {insights.map((insight) => {
                  const sConfig =
                    severityConfig[insight.severity] || severityConfig.low;
                  return (
                    <div
                      key={insight.id}
                      className="group relative p-3 border border-neutral-200 rounded hover:shadow-sm transition-shadow duration-150"
                    >
                      <button
                        onClick={() => handleDismissInsight(insight.id)}
                        className="absolute top-2 right-2 p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-neutral-100 transition-all duration-150"
                        title="Masquer"
                      >
                        <X className="w-3.5 h-3.5 text-neutral-400" />
                      </button>
                      <div className="flex items-start gap-2.5 pr-6">
                        <span
                          className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${sConfig.dotColor}`}
                        />
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-neutral-900 mb-0.5">
                            {insight.title}
                          </p>
                          <p className="text-xs text-neutral-600 leading-relaxed">
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
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Dossiers recents */}
          <Card
            className="animate-fade"
            header={
              <h3 className="font-display text-lg font-semibold text-neutral-900">
                Dossiers recents
              </h3>
            }
          >
            {recentCases.length === 0 ? (
              <EmptyState
                title="Aucun dossier recent"
                description="Vos dossiers apparaitront ici"
                icon={<FolderOpen className="h-12 w-12 text-neutral-300" />}
              />
            ) : (
              <div className="space-y-2">
                {recentCases.slice(0, 5).map((caseItem) => (
                  <div
                    key={caseItem.id}
                    className="flex items-center gap-3 p-3 hover:bg-neutral-50 rounded transition-colors duration-150 cursor-pointer group"
                  >
                    <span
                      className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${getHealthDotColor(caseItem.health_score)}`}
                      title={
                        caseItem.health_score !== undefined
                          ? `Sante: ${caseItem.health_score}/100`
                          : "Sante non evaluee"
                      }
                    />
                    <Badge
                      variant={getStatusVariant(caseItem.status)}
                      size="sm"
                    >
                      {caseItem.status}
                    </Badge>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm text-neutral-900 group-hover:text-primary transition-colors duration-150 truncate">
                        {caseItem.title}
                      </p>
                      <p className="text-xs text-neutral-500 mt-0.5">
                        {getTimeAgo(caseItem.updated_at)}
                      </p>
                    </div>
                    <TrendingUp className="w-4 h-4 text-neutral-300 flex-shrink-0" />
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
                <h3 className="font-display text-lg font-semibold text-neutral-900">
                  Inbox a traiter
                </h3>
                {inboxItems.length > 0 && (
                  <Badge variant="warning" size="sm">
                    {inboxItems.length}
                  </Badge>
                )}
              </div>
            }
          >
            {inboxItems.length === 0 ? (
              <EmptyState
                title="Aucun element en attente"
                description="Votre inbox est vide"
                icon={<InboxIcon className="h-12 w-12 text-neutral-300" />}
              />
            ) : (
              <div className="space-y-2">
                {inboxItems.slice(0, 5).map((item) => {
                  const SourceIcon = sourceIcons[item.source] || Mail;
                  return (
                    <div
                      key={item.id}
                      className="flex items-center gap-3 p-3 hover:bg-neutral-50 rounded transition-colors duration-150 cursor-pointer group"
                    >
                      <div className="p-2 bg-primary/10 rounded flex-shrink-0">
                        <SourceIcon className="w-4 h-4 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-neutral-900 group-hover:text-primary font-medium truncate transition-colors duration-150">
                          {item.subject || "(Sans titre)"}
                        </p>
                        {item.from_name && (
                          <p className="text-xs text-neutral-500 truncate">
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
        {workload.length === 0 ? (
          <EmptyState
            title="Aucune donnee"
            description="Les donnees de charge de travail apparaitront ici"
            icon={<Briefcase className="h-12 w-12 text-neutral-300" />}
          />
        ) : (
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
        )}
      </Card>
    </div>
  );
}
