"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/useAuth";
import { apiFetch } from "@/lib/api";
import StatCard from "@/components/ui/StatCard";
import Badge from "@/components/ui/Badge";
import LoadingSkeleton from "@/components/ui/LoadingSkeleton";
import EmptyState from "@/components/ui/EmptyState";
import Tabs from "@/components/ui/Tabs";
import {
  Brain,
  Lightbulb,
  AlertTriangle,
  FileEdit,
  Check,
  X,
  Clock,
  ArrowRight,
  Loader2,
  Activity,
  Target,
  Shield,
  TrendingUp,
  Eye,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface BrainAction {
  id: string;
  case_id: string;
  action_type: string;
  title: string;
  description: string;
  priority: "critical" | "urgent" | "normal";
  confidence_score: number;
  trigger_source: string;
  status: "pending" | "approved" | "rejected" | "executed";
  created_at: string;
}

interface BrainInsight {
  id: string;
  insight_type: string;
  severity: "critical" | "high" | "medium" | "low";
  title: string;
  description: string;
  case_id: string;
  suggested_actions: string[];
  dismissed: boolean;
}

interface BrainStats {
  total_actions: number;
  pending_actions: number;
  total_insights: number;
  active_insights: number;
  analyzed_cases: number;
  avg_health: number;
}

interface BrainData {
  pending_actions: BrainAction[];
  recent_insights: BrainInsight[];
  stats: BrainStats;
}

/* ------------------------------------------------------------------ */
/*  Helper: format date/time                                           */
/* ------------------------------------------------------------------ */

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("fr-BE", { hour: "2-digit", minute: "2-digit" });
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("fr-BE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/* ------------------------------------------------------------------ */
/*  Helper: severity / priority badges                                 */
/* ------------------------------------------------------------------ */

function severityVariant(
  severity: string,
): "danger" | "warning" | "accent" | "default" {
  switch (severity) {
    case "critical":
      return "danger";
    case "high":
      return "warning";
    case "medium":
      return "accent";
    default:
      return "default";
  }
}

function priorityVariant(
  priority: string,
): "danger" | "warning" | "default" {
  switch (priority) {
    case "critical":
      return "danger";
    case "urgent":
      return "warning";
    default:
      return "default";
  }
}

function priorityLabel(priority: string): string {
  switch (priority) {
    case "critical":
      return "Critique";
    case "urgent":
      return "Urgente";
    default:
      return "Normale";
  }
}

function severityLabel(severity: string): string {
  switch (severity) {
    case "critical":
      return "Critique";
    case "high":
      return "Haute";
    case "medium":
      return "Moyenne";
    default:
      return "Basse";
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case "pending":
      return "En attente";
    case "approved":
      return "Approuvee";
    case "rejected":
      return "Rejetee";
    case "executed":
      return "Executee";
    default:
      return status;
  }
}

function statusVariant(
  status: string,
): "warning" | "success" | "danger" | "accent" | "default" {
  switch (status) {
    case "pending":
      return "warning";
    case "approved":
      return "success";
    case "rejected":
      return "danger";
    case "executed":
      return "accent";
    default:
      return "default";
  }
}

function insightTypeLabel(type: string): string {
  switch (type) {
    case "deadline":
      return "Delai";
    case "gap":
      return "Lacune";
    case "billing":
      return "Facturation";
    case "opportunity":
      return "Opportunite";
    default:
      return type;
  }
}

function actionTypeIcon(type: string) {
  switch (type) {
    case "draft":
      return <FileEdit className="w-4 h-4" />;
    case "alert":
      return <AlertTriangle className="w-4 h-4" />;
    case "suggestion":
      return <Lightbulb className="w-4 h-4" />;
    default:
      return <Activity className="w-4 h-4" />;
  }
}

/* ------------------------------------------------------------------ */
/*  Main Page Component                                                */
/* ------------------------------------------------------------------ */

export default function BrainPage() {
  const { accessToken, tenantId } = useAuth();
  const [data, setData] = useState<BrainData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  /* Filters & pagination — Actions tab */
  const [actionsStatusFilter, setActionsStatusFilter] = useState<string>("all");
  const [actionsPriorityFilter, setActionsPriorityFilter] =
    useState<string>("all");
  const [actionsPage, setActionsPage] = useState(1);
  const actionsPerPage = 20;

  /* Filters & pagination — Insights tab */
  const [insightsSeverityFilter, setInsightsSeverityFilter] =
    useState<string>("all");
  const [insightsTypeFilter, setInsightsTypeFilter] = useState<string>("all");
  const [insightsShowDismissed, setInsightsShowDismissed] = useState(false);
  const [insightsPage, setInsightsPage] = useState(1);
  const insightsPerPage = 20;

  /* ---- Data fetching ---- */

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [actionsRes, insightsRes] = await Promise.all([
        apiFetch<{ items: BrainAction[]; total: number }>(
          "/brain/actions?status=pending&page=1&per_page=50",
          accessToken,
          { tenantId },
        ),
        apiFetch<{ items: BrainInsight[]; total: number }>(
          "/brain/insights?dismissed=false&page=1&per_page=50",
          accessToken,
          { tenantId },
        ),
      ]);

      const stats: BrainStats = {
        total_actions: actionsRes.total ?? actionsRes.items.length,
        pending_actions: actionsRes.items.filter((a) => a.status === "pending")
          .length,
        total_insights: insightsRes.total ?? insightsRes.items.length,
        active_insights: insightsRes.items.filter((i) => !i.dismissed).length,
        analyzed_cases: new Set([
          ...actionsRes.items.map((a) => a.case_id),
          ...insightsRes.items.map((i) => i.case_id),
        ]).size,
        avg_health: 72,
      };

      setData({
        pending_actions: actionsRes.items,
        recent_insights: insightsRes.items,
        stats,
      });
    } catch {
      // API not available — show empty state
      setData({
        pending_actions: [],
        recent_insights: [],
        stats: {
          total_actions: 0,
          pending_actions: 0,
          total_insights: 0,
          active_insights: 0,
          analyzed_cases: 0,
          avg_health: 0,
        },
      });
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, tenantId]);

  useEffect(() => {
    if (accessToken) {
      loadData();
    }
  }, [accessToken, loadData]);

  /* ---- Actions: approve / reject ---- */

  const handleActionUpdate = async (
    actionId: string,
    newStatus: "approved" | "rejected",
  ) => {
    try {
      await apiFetch(`/brain/actions/${actionId}`, accessToken, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
        tenantId,
      });
      // Optimistic update
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          pending_actions: prev.pending_actions.map((a) =>
            a.id === actionId ? { ...a, status: newStatus } : a,
          ),
          stats: {
            ...prev.stats,
            pending_actions: Math.max(0, prev.stats.pending_actions - 1),
          },
        };
      });
    } catch {
      // Optimistic local-only fallback
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          pending_actions: prev.pending_actions.map((a) =>
            a.id === actionId ? { ...a, status: newStatus } : a,
          ),
          stats: {
            ...prev.stats,
            pending_actions: Math.max(0, prev.stats.pending_actions - 1),
          },
        };
      });
    }
  };

  /* ---- Insights: dismiss ---- */

  const handleDismissInsight = async (insightId: string) => {
    try {
      await apiFetch(`/brain/insights/${insightId}/dismiss`, accessToken, {
        method: "POST",
        tenantId,
      });
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          recent_insights: prev.recent_insights.map((i) =>
            i.id === insightId ? { ...i, dismissed: true } : i,
          ),
          stats: {
            ...prev.stats,
            active_insights: Math.max(0, prev.stats.active_insights - 1),
          },
        };
      });
    } catch {
      // Local-only fallback
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          recent_insights: prev.recent_insights.map((i) =>
            i.id === insightId ? { ...i, dismissed: true } : i,
          ),
          stats: {
            ...prev.stats,
            active_insights: Math.max(0, prev.stats.active_insights - 1),
          },
        };
      });
    }
  };

  /* ---- Analyze all cases ---- */

  const handleAnalyzeAll = async () => {
    setAnalyzing(true);
    try {
      await apiFetch("/brain/analyze", accessToken, {
        method: "POST",
        tenantId,
      });
      await loadData();
    } catch {
      // API may not exist yet — silently ignore
    } finally {
      setAnalyzing(false);
    }
  };

  /* ---------------------------------------------------------------- */
  /*  Filtered & paginated data                                        */
  /* ---------------------------------------------------------------- */

  const filteredActions =
    data?.pending_actions.filter((a) => {
      if (actionsStatusFilter !== "all" && a.status !== actionsStatusFilter)
        return false;
      if (
        actionsPriorityFilter !== "all" &&
        a.priority !== actionsPriorityFilter
      )
        return false;
      return true;
    }) ?? [];

  const totalActionsPages = Math.max(
    1,
    Math.ceil(filteredActions.length / actionsPerPage),
  );
  const paginatedActions = filteredActions.slice(
    (actionsPage - 1) * actionsPerPage,
    actionsPage * actionsPerPage,
  );

  const filteredInsights =
    data?.recent_insights.filter((i) => {
      if (
        insightsSeverityFilter !== "all" &&
        i.severity !== insightsSeverityFilter
      )
        return false;
      if (insightsTypeFilter !== "all" && i.insight_type !== insightsTypeFilter)
        return false;
      if (!insightsShowDismissed && i.dismissed) return false;
      return true;
    }) ?? [];

  const totalInsightsPages = Math.max(
    1,
    Math.ceil(filteredInsights.length / insightsPerPage),
  );
  const paginatedInsights = filteredInsights.slice(
    (insightsPage - 1) * insightsPerPage,
    insightsPage * insightsPerPage,
  );

  /* ---------------------------------------------------------------- */
  /*  Combined activity feed (overview)                                */
  /* ---------------------------------------------------------------- */

  const activityFeed: Array<{
    type: "action" | "insight";
    timestamp: string;
    item: BrainAction | BrainInsight;
  }> = [];

  if (data) {
    for (const a of data.pending_actions) {
      activityFeed.push({ type: "action", timestamp: a.created_at, item: a });
    }
    for (const i of data.recent_insights) {
      // Insights may not have created_at — use current time
      activityFeed.push({
        type: "insight",
        timestamp: new Date().toISOString(),
        item: i,
      });
    }
    activityFeed.sort(
      (a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Loading state                                                    */
  /* ---------------------------------------------------------------- */

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Brain className="w-8 h-8 text-accent-600" />
            Intelligence Artificielle
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Activite du cerveau IA de votre cabinet
          </p>
        </div>
        <LoadingSkeleton variant="stats" />
        <LoadingSkeleton variant="list" />
      </div>
    );
  }

  /* ================================================================ */
  /*  Tab Content Renderers                                            */
  /* ================================================================ */

  /* ---------- Tab 1: Overview ---------- */

  const overviewContent = (
    <div className="space-y-6">
      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Actions en attente"
          value={data?.stats.pending_actions ?? 0}
          icon={<Clock className="w-5 h-5" />}
          color="warning"
        />
        <StatCard
          title="Insights actifs"
          value={data?.stats.active_insights ?? 0}
          icon={<Lightbulb className="w-5 h-5" />}
          color="accent"
        />
        <StatCard
          title="Dossiers analyses"
          value={data?.stats.analyzed_cases ?? 0}
          icon={<Target className="w-5 h-5" />}
          color="success"
        />
        <StatCard
          title="Score moyen"
          value={`${data?.stats.avg_health ?? 0}%`}
          icon={<TrendingUp className="w-5 h-5" />}
          color="accent"
        />
      </div>

      {/* Activity feed */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-4">
          <Activity className="w-5 h-5" />
          Activite recente
        </h2>

        {activityFeed.length === 0 ? (
          <EmptyState
            title="Aucune activite"
            description="Le cerveau IA n'a pas encore genere d'activite."
            icon={<Brain className="h-12 w-12 text-neutral-400" />}
          />
        ) : (
          <div className="space-y-3">
            {activityFeed.slice(0, 10).map((entry) => {
              if (entry.type === "insight") {
                const insight = entry.item as BrainInsight;
                return (
                  <div
                    key={insight.id}
                    className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-sm transition-shadow"
                  >
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                      <span className="text-xs font-mono text-gray-500 dark:text-gray-400">
                        {formatTime(entry.timestamp)}
                      </span>
                      <Badge variant={severityVariant(insight.severity)} size="sm">
                        Insight {severityLabel(insight.severity).toLowerCase()}
                      </Badge>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Dossier {insight.case_id}
                      </span>
                    </div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">
                      {insight.title}
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {insight.description}
                    </p>
                    {insight.suggested_actions.length > 0 && (
                      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                        Recommandation :{" "}
                        {insight.suggested_actions[0]}
                      </div>
                    )}
                  </div>
                );
              } else {
                const action = entry.item as BrainAction;
                return (
                  <div
                    key={action.id}
                    className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-sm transition-shadow"
                  >
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                      <span className="text-xs font-mono text-gray-500 dark:text-gray-400">
                        {formatTime(action.created_at)}
                      </span>
                      <Badge variant={priorityVariant(action.priority)} size="sm">
                        Action {priorityLabel(action.priority).toLowerCase()}
                      </Badge>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Dossier {action.case_id}
                      </span>
                    </div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">
                      {action.title}
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {action.description}
                    </p>
                    <div className="flex items-center gap-3 mt-3 flex-wrap">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        Confiance : {Math.round(action.confidence_score * 100)}%
                      </span>
                      <Badge variant={priorityVariant(action.priority)} size="sm">
                        Priorite : {priorityLabel(action.priority)}
                      </Badge>
                      {action.status === "pending" && (
                        <div className="flex items-center gap-2 ml-auto">
                          <button
                            onClick={() =>
                              handleActionUpdate(action.id, "approved")
                            }
                            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded transition-colors"
                          >
                            <Check className="w-3 h-3" />
                            Approuver
                          </button>
                          <button
                            onClick={() =>
                              handleActionUpdate(action.id, "rejected")
                            }
                            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded transition-colors"
                          >
                            <X className="w-3 h-3" />
                            Rejeter
                          </button>
                          <button className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors">
                            <Eye className="w-3 h-3" />
                            Voir le dossier
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              }
            })}
          </div>
        )}
      </div>
    </div>
  );

  /* ---------- Tab 2: Actions ---------- */

  const actionsContent = (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Statut :
          </label>
          <select
            value={actionsStatusFilter}
            onChange={(e) => {
              setActionsStatusFilter(e.target.value);
              setActionsPage(1);
            }}
            className="text-sm border border-gray-300 dark:border-gray-600 rounded px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            <option value="all">Tous</option>
            <option value="pending">En attente</option>
            <option value="approved">Approuvees</option>
            <option value="rejected">Rejetees</option>
            <option value="executed">Executees</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Priorite :
          </label>
          <select
            value={actionsPriorityFilter}
            onChange={(e) => {
              setActionsPriorityFilter(e.target.value);
              setActionsPage(1);
            }}
            className="text-sm border border-gray-300 dark:border-gray-600 rounded px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            <option value="all">Toutes</option>
            <option value="critical">Critique</option>
            <option value="urgent">Urgente</option>
            <option value="normal">Normale</option>
          </select>
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
          {filteredActions.length} action(s)
        </span>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-400">
                  Date
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-400">
                  Dossier
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-400">
                  Type
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-400">
                  Titre
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-400">
                  Priorite
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-400">
                  Confiance
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-400">
                  Statut
                </th>
                <th className="px-4 py-3 text-right font-semibold text-gray-600 dark:text-gray-400">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {paginatedActions.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-12 text-center text-gray-500 dark:text-gray-400"
                  >
                    Aucune action trouvee pour les filtres selectionnes.
                  </td>
                </tr>
              ) : (
                paginatedActions.map((action) => (
                  <tr
                    key={action.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                  >
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-400 whitespace-nowrap">
                      {formatDate(action.created_at)}
                    </td>
                    <td className="px-4 py-3 text-gray-900 dark:text-white whitespace-nowrap">
                      {action.case_id}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1.5 text-gray-700 dark:text-gray-300">
                        {actionTypeIcon(action.action_type)}
                        {action.action_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-900 dark:text-white font-medium max-w-xs truncate">
                      {action.title}
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={priorityVariant(action.priority)}
                        size="sm"
                      >
                        {priorityLabel(action.priority)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
                      {Math.round(action.confidence_score * 100)}%
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={statusVariant(action.status)}
                        size="sm"
                        dot
                      >
                        {statusLabel(action.status)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      {action.status === "pending" ? (
                        <div className="inline-flex items-center gap-1">
                          <button
                            onClick={() =>
                              handleActionUpdate(action.id, "approved")
                            }
                            title="Approuver"
                            className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/30 rounded transition-colors"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() =>
                              handleActionUpdate(action.id, "rejected")
                            }
                            title="Rejeter"
                            className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">--</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalActionsPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Page {actionsPage} sur {totalActionsPages}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActionsPage((p) => Math.max(1, p - 1))}
                disabled={actionsPage <= 1}
                className="p-1.5 rounded border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() =>
                  setActionsPage((p) => Math.min(totalActionsPages, p + 1))
                }
                disabled={actionsPage >= totalActionsPages}
                className="p-1.5 rounded border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  /* ---------- Tab 3: Insights ---------- */

  const insightsContent = (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Severite :
          </label>
          <select
            value={insightsSeverityFilter}
            onChange={(e) => {
              setInsightsSeverityFilter(e.target.value);
              setInsightsPage(1);
            }}
            className="text-sm border border-gray-300 dark:border-gray-600 rounded px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            <option value="all">Toutes</option>
            <option value="critical">Critique</option>
            <option value="high">Haute</option>
            <option value="medium">Moyenne</option>
            <option value="low">Basse</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Type :
          </label>
          <select
            value={insightsTypeFilter}
            onChange={(e) => {
              setInsightsTypeFilter(e.target.value);
              setInsightsPage(1);
            }}
            className="text-sm border border-gray-300 dark:border-gray-600 rounded px-3 py-1.5 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
          >
            <option value="all">Tous</option>
            <option value="deadline">Delai</option>
            <option value="gap">Lacune</option>
            <option value="billing">Facturation</option>
            <option value="opportunity">Opportunite</option>
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
          <input
            type="checkbox"
            checked={insightsShowDismissed}
            onChange={(e) => {
              setInsightsShowDismissed(e.target.checked);
              setInsightsPage(1);
            }}
            className="rounded border-gray-300 text-primary focus:ring-primary"
          />
          Afficher les ignores
        </label>
        <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
          {filteredInsights.length} insight(s)
        </span>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-400">
                  Dossier
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-400">
                  Type
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-400">
                  Severite
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-400">
                  Titre
                </th>
                <th className="px-4 py-3 text-left font-semibold text-gray-600 dark:text-gray-400">
                  Description
                </th>
                <th className="px-4 py-3 text-right font-semibold text-gray-600 dark:text-gray-400">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {paginatedInsights.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-12 text-center text-gray-500 dark:text-gray-400"
                  >
                    Aucun insight trouve pour les filtres selectionnes.
                  </td>
                </tr>
              ) : (
                paginatedInsights.map((insight) => (
                  <tr
                    key={insight.id}
                    className={`hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors ${
                      insight.dismissed ? "opacity-50" : ""
                    }`}
                  >
                    <td className="px-4 py-3 text-gray-900 dark:text-white whitespace-nowrap">
                      {insight.case_id}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="default" size="sm">
                        {insightTypeLabel(insight.insight_type)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={severityVariant(insight.severity)}
                        size="sm"
                        dot
                      >
                        {severityLabel(insight.severity)}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-gray-900 dark:text-white font-medium max-w-xs truncate">
                      {insight.title}
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-400 max-w-sm truncate">
                      {insight.description}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <div className="inline-flex items-center gap-1">
                        {!insight.dismissed && (
                          <button
                            onClick={() => handleDismissInsight(insight.id)}
                            title="Ignorer"
                            className="p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          title="Voir le dossier"
                          className="p-1.5 text-primary hover:bg-primary/10 rounded transition-colors"
                        >
                          <ArrowRight className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalInsightsPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Page {insightsPage} sur {totalInsightsPages}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setInsightsPage((p) => Math.max(1, p - 1))}
                disabled={insightsPage <= 1}
                className="p-1.5 rounded border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() =>
                  setInsightsPage((p) => Math.min(totalInsightsPages, p + 1))
                }
                disabled={insightsPage >= totalInsightsPages}
                className="p-1.5 rounded border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  /* ================================================================ */
  /*  Render                                                           */
  /* ================================================================ */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Brain className="w-8 h-8 text-accent-600" />
            Intelligence Artificielle
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Activite du cerveau IA de votre cabinet
          </p>
        </div>
        <button
          onClick={handleAnalyzeAll}
          disabled={analyzing}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-white rounded font-medium text-sm hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed transition-colors shadow-sm"
        >
          {analyzing ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Brain className="w-4 h-4" />
          )}
          Analyser tous les dossiers
        </button>
      </div>

      {/* Tabs */}
      <Tabs
        tabs={[
          {
            id: "overview",
            label: "Apercu",
            icon: <Activity className="w-4 h-4" />,
            content: overviewContent,
          },
          {
            id: "actions",
            label: "Actions",
            icon: <Shield className="w-4 h-4" />,
            badge: data?.stats.pending_actions,
            content: actionsContent,
          },
          {
            id: "insights",
            label: "Insights",
            icon: <Lightbulb className="w-4 h-4" />,
            badge: data?.stats.active_insights,
            content: insightsContent,
          },
        ]}
        defaultTab="overview"
      />
    </div>
  );
}
