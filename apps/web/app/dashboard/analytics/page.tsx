"use client";

import { useAuth } from "@/lib/useAuth";
import { useEffect, useState, useCallback, useMemo } from "react";
import {
  Euro,
  Clock,
  Briefcase,
  Percent,
  TrendingUp,
  TrendingDown,
  ArrowUp,
  ArrowDown,
  AlertTriangle,
  CalendarClock,
  ChevronDown,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { apiFetch } from "@/lib/api";
import {
  LoadingSkeleton,
  ErrorState,
  Card,
  Badge,
} from "@/components/ui";

/* ─────────────────────────── Types ─────────────────────────── */

interface DashboardStats {
  total_cases: number;
  total_contacts: number;
  monthly_hours: number;
  total_invoices: number;
  total_documents: number;
  pending_inbox: number;
  total_invoiced?: number;
  total_hours?: number;
  recovery_rate?: number;
}

interface BrainSummaryResponse {
  total_active_cases: number;
  risk_distribution: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
  critical_deadlines: {
    id: string;
    title: string;
    case_name: string;
    due_date: string;
    days_remaining: number;
    urgency: string;
  }[];
  cases_needing_attention: number;
  health_score: number;
}

type Period = "7d" | "30d" | "90d" | "12m";
type SortKey = "ref" | "title" | "type" | "hours" | "amount" | "rate";
type SortDir = "asc" | "desc";

/* ─────────────────────────── Mock Data ─────────────────────────── */

const revenueData = [
  { month: "Sep", revenue: 28500, hours: 142 },
  { month: "Oct", revenue: 32100, hours: 156 },
  { month: "Nov", revenue: 29800, hours: 148 },
  { month: "Dec", revenue: 24200, hours: 121 },
  { month: "Jan", revenue: 35600, hours: 178 },
  { month: "Fev", revenue: 31400, hours: 157 },
];

const caseDistribution = [
  { name: "Civil", value: 35, color: "#3b82f6" },
  { name: "Penal", value: 18, color: "#ef4444" },
  { name: "Commercial", value: 22, color: "#f59e0b" },
  { name: "Familial", value: 12, color: "#8b5cf6" },
  { name: "Fiscal", value: 8, color: "#10b981" },
  { name: "Social", value: 5, color: "#6366f1" },
];

const caseStatus = [
  { status: "Ouvert", count: 12, color: "#3b82f6" },
  { status: "En cours", count: 28, color: "#f59e0b" },
  { status: "En attente", count: 8, color: "#94a3b8" },
  { status: "Cloture", count: 45, color: "#10b981" },
];

const workloadData = [
  { week: "S06", billable: 32, nonBillable: 8 },
  { week: "S07", billable: 38, nonBillable: 6 },
  { week: "S08", billable: 35, nonBillable: 10 },
  { week: "S09", billable: 28, nonBillable: 12 },
];

const topCases = [
  { ref: "2024/0142", title: "Dupont c/ SA Construct", type: "Civil", hours: 45.5, amount: 13650, rate: 300 },
  { ref: "2024/0156", title: "Janssens - Succession", type: "Familial", hours: 38.0, amount: 11400, rate: 300 },
  { ref: "2024/0178", title: "SPRL Tech Innov - Litige commercial", type: "Commercial", hours: 32.5, amount: 16250, rate: 500 },
  { ref: "2024/0189", title: "Maes - Licenciement abusif", type: "Social", hours: 28.0, amount: 7000, rate: 250 },
  { ref: "2024/0195", title: "SA Immo Nord - Bail commercial", type: "Civil", hours: 22.5, amount: 6750, rate: 300 },
];

/* ─────────────────────────── Helpers ─────────────────────────── */

const eurFormatter = new Intl.NumberFormat("fr-BE", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const eurFormatterFull = new Intl.NumberFormat("fr-BE", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const numberFormatter = new Intl.NumberFormat("fr-BE");

const PERIOD_OPTIONS: { value: Period; label: string }[] = [
  { value: "7d", label: "7 jours" },
  { value: "30d", label: "30 jours" },
  { value: "90d", label: "90 jours" },
  { value: "12m", label: "12 mois" },
];

function getRiskColor(level: string): string {
  switch (level) {
    case "critical":
      return "bg-danger-500";
    case "high":
      return "bg-warning-500";
    case "medium":
      return "bg-yellow-400";
    case "low":
      return "bg-success-500";
    default:
      return "bg-neutral-300";
  }
}

function getRiskLabel(level: string): string {
  switch (level) {
    case "critical":
      return "Critique";
    case "high":
      return "Eleve";
    case "medium":
      return "Moyen";
    case "low":
      return "Faible";
    default:
      return level;
  }
}

/* ─────────────────────────── Custom Tooltip Components ─────────────────────────── */

function RevenueTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number; dataKey: string }>; label?: string }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="bg-white border border-neutral-200 rounded shadow-lg p-3">
      <p className="text-sm font-semibold text-neutral-900 mb-1">{label}</p>
      {payload.map((entry, index) => (
        <p key={index} className="text-xs text-neutral-600">
          {entry.dataKey === "revenue" ? "Chiffre d'affaires" : "Heures"} :{" "}
          <span className="font-medium text-neutral-900">
            {entry.dataKey === "revenue" ? eurFormatter.format(entry.value) : `${entry.value}h`}
          </span>
        </p>
      ))}
    </div>
  );
}

function PieTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number; payload: { color: string } }> }) {
  if (!active || !payload || payload.length === 0) return null;
  const total = caseDistribution.reduce((sum, d) => sum + d.value, 0);
  const entry = payload[0];
  const pct = ((entry.value / total) * 100).toFixed(1);
  return (
    <div className="bg-white border border-neutral-200 rounded shadow-lg p-3">
      <div className="flex items-center gap-2 mb-1">
        <span
          className="w-3 h-3 rounded-sm flex-shrink-0"
          style={{ backgroundColor: entry.payload.color }}
        />
        <span className="text-sm font-semibold text-neutral-900">{entry.name}</span>
      </div>
      <p className="text-xs text-neutral-600">
        {entry.value} dossiers ({pct}%)
      </p>
    </div>
  );
}

function StatusTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="bg-white border border-neutral-200 rounded shadow-lg p-3">
      <p className="text-sm font-semibold text-neutral-900 mb-1">{label}</p>
      <p className="text-xs text-neutral-600">
        {payload[0].value} dossiers
      </p>
    </div>
  );
}

function WorkloadTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number; dataKey: string; color: string }>; label?: string }) {
  if (!active || !payload || payload.length === 0) return null;
  const total = payload.reduce((sum, p) => sum + p.value, 0);
  return (
    <div className="bg-white border border-neutral-200 rounded shadow-lg p-3">
      <p className="text-sm font-semibold text-neutral-900 mb-1">Semaine {label}</p>
      {payload.map((entry, index) => (
        <p key={index} className="text-xs text-neutral-600">
          <span
            className="inline-block w-2 h-2 rounded-sm mr-1.5"
            style={{ backgroundColor: entry.color }}
          />
          {entry.dataKey === "billable" ? "Facturable" : "Non facturable"} :{" "}
          <span className="font-medium text-neutral-900">{entry.value}h</span>
        </p>
      ))}
      <p className="text-xs text-neutral-500 mt-1 pt-1 border-t border-neutral-100">
        Total : <span className="font-medium">{total}h</span>
      </p>
    </div>
  );
}

/* ─────────────────────────── Component ─────────────────────────── */

export default function AnalyticsPage() {
  const { accessToken, tenantId } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<Period>("30d");
  const [periodOpen, setPeriodOpen] = useState(false);

  // API data
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [brainData, setBrainData] = useState<BrainSummaryResponse | null>(null);

  // Table sort
  const [sortKey, setSortKey] = useState<SortKey>("amount");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const fetchData = useCallback(async () => {
    if (!accessToken) return;
    try {
      setLoading(true);
      setError(null);

      const [statsRes, brainRes] = await Promise.all([
        apiFetch<{ stats?: DashboardStats }>("/dashboard/stats", accessToken, {
          tenantId,
        }).catch(() => ({})),
        apiFetch<BrainSummaryResponse>("/brain/summary", accessToken, {
          tenantId,
        }).catch(() => null),
      ]);

      const dashStats =
        statsRes && "stats" in statsRes && statsRes.stats
          ? statsRes.stats
          : null;
      setStats(dashStats);
      setBrainData(brainRes);
    } catch {
      setError("Impossible de charger les donnees analytiques");
    } finally {
      setLoading(false);
    }
  }, [accessToken, tenantId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* ── KPI values (from API or fallback) ── */
  const totalInvoiced = stats?.total_invoiced ?? 181600;
  const totalHours = stats?.total_hours ?? stats?.monthly_hours ?? 902;
  const totalCases = stats?.total_cases ?? 93;
  const recoveryRate = stats?.recovery_rate ?? 87;

  /* ── Sorted top cases ── */
  const sortedCases = useMemo(() => {
    return [...topCases].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortDir === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDir === "asc" ? aVal - bVal : bVal - aVal;
      }
      return 0;
    });
  }, [sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  /* ── Brain Intelligence data ── */
  const riskDistribution = brainData?.risk_distribution ?? {
    low: 42,
    medium: 28,
    high: 15,
    critical: 8,
  };

  const casesNeedingAttention = brainData?.cases_needing_attention ?? 5;

  const criticalDeadlines = brainData?.critical_deadlines?.length
    ? brainData.critical_deadlines
    : [
        { id: "d1", title: "Conclusions -- Dupont c/ Immobel", case_name: "Dupont c/ Immobel SA", due_date: "2026-02-24", days_remaining: 4, urgency: "critical" },
        { id: "d2", title: "Audience -- TPI Bruxelles", case_name: "TPI Bruxelles - Janssens", due_date: "2026-02-28", days_remaining: 8, urgency: "urgent" },
        { id: "d3", title: "Delai d'appel -- Janssens", case_name: "Janssens c/ Etat belge", due_date: "2026-03-05", days_remaining: 13, urgency: "attention" },
      ];

  const totalRisk = riskDistribution.low + riskDistribution.medium + riskDistribution.high + riskDistribution.critical;

  /* ── Loading / Error states ── */
  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 p-6">
        <LoadingSkeleton variant="stats" />
        <div className="mt-8">
          <LoadingSkeleton variant="card" />
        </div>
        <div className="mt-8">
          <LoadingSkeleton variant="table" />
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

  /* ── Pie chart custom label ── */
  const totalPieValue = caseDistribution.reduce((sum, d) => sum + d.value, 0);

  /* eslint-disable @typescript-eslint/no-explicit-any */
  const renderPieLabel = (props: any) => {
    const { cx, cy, midAngle, innerRadius, outerRadius, percent } = props;

    if (!percent || percent < 0.07) return null;
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor="middle"
        dominantBaseline="central"
        className="text-xs font-medium"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };
  /* eslint-enable @typescript-eslint/no-explicit-any */

  /* ── Render ── */
  return (
    <div className="min-h-screen bg-neutral-50">
      {/* ═══════════════════ Page Header ═══════════════════ */}
      <div className="mb-6 animate-fade">
        <div className="relative overflow-hidden bg-white border border-neutral-200 p-8 md:p-10">
          <div className="relative z-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl md:text-4xl font-display font-bold text-primary mb-2">
                Analytique &amp; Rapports
              </h1>
              <p className="text-base text-neutral-600">
                Vue d&apos;ensemble de la performance du cabinet
              </p>
            </div>

            {/* Period selector */}
            <div className="relative">
              <button
                onClick={() => setPeriodOpen(!periodOpen)}
                className="flex items-center gap-2 px-4 py-2.5 bg-white border border-neutral-300 rounded shadow-sm text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors duration-150"
              >
                {PERIOD_OPTIONS.find((p) => p.value === period)?.label}
                <ChevronDown
                  className={`w-4 h-4 text-neutral-400 transition-transform duration-150 ${
                    periodOpen ? "rotate-180" : ""
                  }`}
                />
              </button>
              {periodOpen && (
                <div className="absolute right-0 mt-1 w-36 bg-white border border-neutral-200 rounded shadow-lg z-20">
                  {PERIOD_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => {
                        setPeriod(opt.value);
                        setPeriodOpen(false);
                      }}
                      className={`w-full text-left px-4 py-2.5 text-sm transition-colors duration-150 ${
                        period === opt.value
                          ? "bg-primary/5 text-primary font-medium"
                          : "text-neutral-700 hover:bg-neutral-50"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════════════ Section 1: KPI Cards ═══════════════════ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 animate-fade">
        {/* Chiffre d'affaires */}
        <div className="bg-white rounded shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-neutral-700">
              Chiffre d&apos;affaires
            </h3>
            <div className="p-2 rounded bg-accent-100 text-accent-600">
              <Euro className="w-5 h-5" />
            </div>
          </div>
          <div className="mb-2">
            <p className="text-3xl font-bold text-neutral-900">
              {eurFormatter.format(totalInvoiced)}
            </p>
          </div>
          <div className="flex items-center space-x-1">
            <TrendingUp className="h-4 w-4 text-success-600" />
            <span className="text-sm font-medium text-success-600">+12%</span>
            <span className="text-sm text-neutral-600">vs periode prec.</span>
          </div>
        </div>

        {/* Heures facturees */}
        <div className="bg-white rounded shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-neutral-700">
              Heures facturees
            </h3>
            <div className="p-2 rounded bg-success-100 text-success-600">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mb-2">
            <p className="text-3xl font-bold text-neutral-900">
              {numberFormatter.format(totalHours)}
            </p>
          </div>
          <div className="flex items-center space-x-1">
            <TrendingUp className="h-4 w-4 text-success-600" />
            <span className="text-sm font-medium text-success-600">+8%</span>
            <span className="text-sm text-neutral-600">vs periode prec.</span>
          </div>
        </div>

        {/* Dossiers actifs */}
        <div className="bg-white rounded shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-neutral-700">
              Dossiers actifs
            </h3>
            <div className="p-2 rounded bg-warning-100 text-warning-600">
              <Briefcase className="w-5 h-5" />
            </div>
          </div>
          <div className="mb-2">
            <p className="text-3xl font-bold text-neutral-900">{totalCases}</p>
          </div>
          <div className="flex items-center space-x-1">
            <TrendingDown className="h-4 w-4 text-error-600" />
            <span className="text-sm font-medium text-error-600">-3%</span>
            <span className="text-sm text-neutral-600">vs periode prec.</span>
          </div>
        </div>

        {/* Taux de recouvrement */}
        <div className="bg-white rounded shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-neutral-700">
              Taux de recouvrement
            </h3>
            <div className="p-2 rounded bg-accent-100 text-accent-600">
              <Percent className="w-5 h-5" />
            </div>
          </div>
          <div className="mb-2">
            <p className="text-3xl font-bold text-neutral-900">{recoveryRate}%</p>
          </div>
          <div className="flex items-center space-x-1">
            <TrendingUp className="h-4 w-4 text-success-600" />
            <span className="text-sm font-medium text-success-600">+5%</span>
            <span className="text-sm text-neutral-600">vs periode prec.</span>
          </div>
        </div>
      </div>

      {/* ═══════════════════ Section 2: Revenue Chart ═══════════════════ */}
      <Card
        className="mb-6 animate-fade"
        header={
          <div className="flex items-center justify-between">
            <h3 className="font-display text-lg font-semibold text-neutral-900">
              Evolution du chiffre d&apos;affaires
            </h3>
            <Badge variant="accent" size="sm">
              6 derniers mois
            </Badge>
          </div>
        }
      >
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={revenueData}
              margin={{ top: 10, right: 30, left: 10, bottom: 0 }}
            >
              <defs>
                <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 12, fill: "#6b7280" }}
                axisLine={{ stroke: "#e5e7eb" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 12, fill: "#6b7280" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(value: number) => eurFormatter.format(value)}
              />
              <Tooltip content={<RevenueTooltip />} />
              <Area
                type="monotone"
                dataKey="revenue"
                stroke="#3b82f6"
                strokeWidth={2.5}
                fill="url(#revenueGradient)"
                dot={{ r: 4, fill: "#3b82f6", strokeWidth: 2, stroke: "#fff" }}
                activeDot={{ r: 6, fill: "#3b82f6", strokeWidth: 2, stroke: "#fff" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* ═══════════════════ Section 3: Two-Column Charts ═══════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Case Distribution - Pie Chart */}
        <Card
          className="animate-fade"
          header={
            <h3 className="font-display text-lg font-semibold text-neutral-900">
              Repartition par type de dossier
            </h3>
          }
        >
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={caseDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={renderPieLabel}
                  outerRadius={110}
                  innerRadius={50}
                  dataKey="value"
                  strokeWidth={2}
                  stroke="#fff"
                >
                  {caseDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<PieTooltip />} />
                <Legend
                  layout="vertical"
                  verticalAlign="middle"
                  align="right"
                  iconType="circle"
                  iconSize={8}
                  formatter={(value: string) => {
                    const item = caseDistribution.find((d) => d.name === value);
                    const pct = item
                      ? ((item.value / totalPieValue) * 100).toFixed(0)
                      : "0";
                    return (
                      <span className="text-sm text-neutral-700">
                        {value}{" "}
                        <span className="text-neutral-400">({pct}%)</span>
                      </span>
                    );
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Case Status - Bar Chart */}
        <Card
          className="animate-fade"
          header={
            <h3 className="font-display text-lg font-semibold text-neutral-900">
              Statut des dossiers
            </h3>
          }
        >
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={caseStatus}
                layout="vertical"
                margin={{ top: 10, right: 30, left: 20, bottom: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fontSize: 12, fill: "#6b7280" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="status"
                  tick={{ fontSize: 13, fill: "#374151", fontWeight: 500 }}
                  axisLine={false}
                  tickLine={false}
                  width={90}
                />
                <Tooltip content={<StatusTooltip />} />
                <Bar
                  dataKey="count"
                  radius={[0, 6, 6, 0]}
                  barSize={28}
                >
                  {caseStatus.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* ═══════════════════ Section 4: Workload Analysis ═══════════════════ */}
      <Card
        className="mb-6 animate-fade"
        header={
          <div className="flex items-center justify-between">
            <h3 className="font-display text-lg font-semibold text-neutral-900">
              Analyse de la charge de travail
            </h3>
            <div className="flex items-center gap-4 text-xs text-neutral-500">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: "#3b82f6" }} />
                Facturable
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: "#94a3b8" }} />
                Non facturable
              </span>
            </div>
          </div>
        }
      >
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={workloadData}
              margin={{ top: 10, right: 30, left: 10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="week"
                tick={{ fontSize: 12, fill: "#6b7280" }}
                axisLine={{ stroke: "#e5e7eb" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 12, fill: "#6b7280" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(value: number) => `${value}h`}
              />
              <Tooltip content={<WorkloadTooltip />} />
              <Bar
                dataKey="billable"
                stackId="workload"
                fill="#3b82f6"
                radius={[0, 0, 0, 0]}
                barSize={40}
              />
              <Bar
                dataKey="nonBillable"
                stackId="workload"
                fill="#94a3b8"
                radius={[4, 4, 0, 0]}
                barSize={40}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* ═══════════════════ Section 5: Performance Table ═══════════════════ */}
      <Card
        className="mb-6 animate-fade"
        header={
          <div className="flex items-center justify-between">
            <h3 className="font-display text-lg font-semibold text-neutral-900">
              Top dossiers par chiffre d&apos;affaires
            </h3>
            <Badge variant="default" size="sm">
              {topCases.length} dossiers
            </Badge>
          </div>
        }
      >
        <div className="overflow-x-auto -mx-6 -mb-6">
          <table className="w-full">
            <thead className="bg-neutral-50 border-b border-neutral-200">
              <tr>
                {[
                  { key: "ref" as SortKey, label: "Ref." },
                  { key: "title" as SortKey, label: "Titre" },
                  { key: "type" as SortKey, label: "Type" },
                  { key: "hours" as SortKey, label: "Heures" },
                  { key: "amount" as SortKey, label: "Montant facture" },
                  { key: "rate" as SortKey, label: "Taux horaire effectif" },
                ].map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="px-6 py-3 text-left text-xs font-semibold text-neutral-600 uppercase tracking-wider cursor-pointer select-none hover:bg-neutral-100 transition-colors duration-150"
                  >
                    <div className="flex items-center gap-1.5">
                      <span>{col.label}</span>
                      {sortKey === col.key ? (
                        sortDir === "asc" ? (
                          <ArrowUp className="w-3 h-3 text-primary" />
                        ) : (
                          <ArrowDown className="w-3 h-3 text-primary" />
                        )
                      ) : (
                        <ArrowUp className="w-3 h-3 opacity-0" />
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {sortedCases.map((c) => (
                <tr
                  key={c.ref}
                  className="hover:bg-neutral-50 transition-colors duration-150"
                >
                  <td className="px-6 py-4 text-sm font-medium text-primary whitespace-nowrap">
                    {c.ref}
                  </td>
                  <td className="px-6 py-4 text-sm text-neutral-900 max-w-xs truncate">
                    {c.title}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <Badge
                      variant={
                        c.type === "Civil"
                          ? "accent"
                          : c.type === "Commercial"
                            ? "warning"
                            : c.type === "Familial"
                              ? "default"
                              : c.type === "Social"
                                ? "success"
                                : "neutral"
                      }
                      size="sm"
                    >
                      {c.type}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 text-sm text-neutral-700 whitespace-nowrap">
                    {c.hours.toFixed(1)}h
                  </td>
                  <td className="px-6 py-4 text-sm font-semibold text-neutral-900 whitespace-nowrap">
                    {eurFormatterFull.format(c.amount)}
                  </td>
                  <td className="px-6 py-4 text-sm text-neutral-700 whitespace-nowrap">
                    {eurFormatter.format(c.rate)}/h
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* ═══════════════════ Section 6: Intelligence Summary ═══════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Risk Distribution */}
        <Card
          className="animate-fade"
          header={
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-warning-600" />
              <h3 className="font-display text-lg font-semibold text-neutral-900">
                Distribution des risques
              </h3>
            </div>
          }
        >
          <div className="space-y-4">
            {(["critical", "high", "medium", "low"] as const).map((level) => {
              const count = riskDistribution[level];
              const pct = totalRisk > 0 ? (count / totalRisk) * 100 : 0;
              return (
                <div key={level}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-neutral-700">
                      {getRiskLabel(level)}
                    </span>
                    <span className="text-sm font-semibold text-neutral-900">
                      {count}
                    </span>
                  </div>
                  <div className="w-full bg-neutral-100 rounded-full h-2.5">
                    <div
                      className={`h-2.5 rounded-full transition-all duration-500 ${getRiskColor(level)}`}
                      style={{ width: `${Math.max(pct, 2)}%` }}
                    />
                  </div>
                </div>
              );
            })}
            <div className="pt-2 border-t border-neutral-100">
              <p className="text-xs text-neutral-500">
                Total : <span className="font-medium text-neutral-700">{totalRisk}</span> dossiers evalues
              </p>
            </div>
          </div>
        </Card>

        {/* Cases Needing Attention */}
        <Card
          className="animate-fade"
          header={
            <div className="flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-primary" />
              <h3 className="font-display text-lg font-semibold text-neutral-900">
                Dossiers a surveiller
              </h3>
            </div>
          }
        >
          <div className="flex flex-col items-center justify-center py-4">
            <p className="text-5xl font-bold text-neutral-900 mb-2">
              {casesNeedingAttention}
            </p>
            <p className="text-sm text-neutral-600 mb-4">
              dossiers necessitant une attention
            </p>
            <div className="w-full space-y-2">
              <div className="flex items-center justify-between p-3 bg-danger-50 rounded border border-danger-100">
                <span className="text-sm text-neutral-700">Risque eleve</span>
                <Badge variant="danger" size="sm">
                  {riskDistribution.critical + riskDistribution.high}
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 bg-warning-50 rounded border border-warning-100">
                <span className="text-sm text-neutral-700">Echeances proches</span>
                <Badge variant="warning" size="sm">
                  {criticalDeadlines.filter((d) => d.days_remaining <= 7).length}
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 bg-neutral-50 rounded border border-neutral-200">
                <span className="text-sm text-neutral-700">Factures en retard</span>
                <Badge variant="neutral" size="sm">3</Badge>
              </div>
            </div>
          </div>
        </Card>

        {/* Critical Deadlines */}
        <Card
          className="animate-fade"
          header={
            <div className="flex items-center gap-2">
              <CalendarClock className="w-5 h-5 text-danger-600" />
              <h3 className="font-display text-lg font-semibold text-neutral-900">
                Echeances critiques
              </h3>
            </div>
          }
        >
          <div className="space-y-3">
            {criticalDeadlines.slice(0, 5).map((deadline) => {
              const urgencyColors: Record<string, string> = {
                critical: "border-l-danger-500 bg-danger-50/50",
                urgent: "border-l-warning-500 bg-warning-50/30",
                attention: "border-l-yellow-400 bg-yellow-50/30",
                normal: "border-l-neutral-300",
              };
              const colorClass =
                urgencyColors[deadline.urgency] || urgencyColors.normal;

              return (
                <div
                  key={deadline.id}
                  className={`p-3 rounded border-l-4 ${colorClass}`}
                >
                  <p className="text-sm font-semibold text-neutral-900 mb-0.5">
                    {deadline.title}
                  </p>
                  <p className="text-xs text-neutral-500 mb-1">
                    {deadline.case_name}
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-neutral-500">
                      {new Date(deadline.due_date).toLocaleDateString("fr-FR", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                    <Badge
                      variant={
                        deadline.days_remaining <= 3
                          ? "danger"
                          : deadline.days_remaining <= 7
                            ? "warning"
                            : "default"
                      }
                      size="sm"
                    >
                      {deadline.days_remaining}j
                    </Badge>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}
