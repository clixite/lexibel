"use client";

import { useEffect, useState } from "react";
import {
  Clock,
  FileText,
  CreditCard,
  AlertTriangle,
  TrendingUp,
  Brain,
  Loader2,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface BillingDashboardProps {
  accessToken: string;
  tenantId: string;
  onCreateInvoice?: (caseId?: string) => void;
}

interface TimeEntry {
  id: string;
  duration_minutes: number;
  status: string;
  case_id: string;
  hourly_rate_cents: number | null;
  date: string;
}

interface Invoice {
  id: string;
  invoice_number: string;
  subtotal_cents: number;
  vat_cents: number;
  total_cents: number;
  status: string;
  case_id: string;
  created_at: string;
}

interface BillingReport {
  recovery_rate: number;
  unbilled_hours: number;
  unbilled_amount_cents: number;
  anomalies: { description: string; severity: string }[];
  suggestions: {
    case_id: string;
    case_title: string;
    unbilled_hours: number;
    estimated_amount_cents: number;
  }[];
  recommendations: string[];
}

/* ------------------------------------------------------------------ */
/*  Mock data                                                          */
/* ------------------------------------------------------------------ */

const MOCK_REVENUE_DATA = [
  { month: "Sep", facture: 12500, encaisse: 9800 },
  { month: "Oct", facture: 18200, encaisse: 14500 },
  { month: "Nov", facture: 15800, encaisse: 16200 },
  { month: "Dec", facture: 22100, encaisse: 18900 },
  { month: "Jan", facture: 19400, encaisse: 17200 },
  { month: "Fev", facture: 16700, encaisse: 15100 },
];

const MOCK_TOP_CASES = [
  {
    reference: "DOS-2025-042",
    title: "Succession Dupont",
    hours: 42.5,
    facture: 637500,
    encaisse: 510000,
  },
  {
    reference: "DOS-2025-038",
    title: "Litige commercial SA Belvaux",
    hours: 36.0,
    facture: 540000,
    encaisse: 540000,
  },
  {
    reference: "DOS-2025-051",
    title: "Divorce Martin/Leroy",
    hours: 28.75,
    facture: 431250,
    encaisse: 345000,
  },
  {
    reference: "DOS-2025-045",
    title: "Bail commercial Rue Neuve",
    hours: 18.0,
    facture: 270000,
    encaisse: 270000,
  },
  {
    reference: "DOS-2025-049",
    title: "Contestation fiscale SPRL Artisan",
    hours: 15.5,
    facture: 232500,
    encaisse: 186000,
  },
];

const MOCK_BILLING_REPORT: BillingReport = {
  recovery_rate: 82.4,
  unbilled_hours: 47.5,
  unbilled_amount_cents: 712500,
  anomalies: [
    {
      description:
        "Le dossier DOS-2025-051 a 12h non facturees depuis plus de 30 jours.",
      severity: "warning",
    },
    {
      description:
        "La facture FACT-2025-089 est en retard de paiement de 45 jours.",
      severity: "danger",
    },
    {
      description:
        "Taux horaire inhabituellement bas sur le dossier DOS-2025-049.",
      severity: "warning",
    },
  ],
  suggestions: [
    {
      case_id: "case-1",
      case_title: "Succession Dupont",
      unbilled_hours: 8.5,
      estimated_amount_cents: 127500,
    },
    {
      case_id: "case-2",
      case_title: "Divorce Martin/Leroy",
      unbilled_hours: 12.0,
      estimated_amount_cents: 180000,
    },
    {
      case_id: "case-3",
      case_title: "Contestation fiscale SPRL Artisan",
      unbilled_hours: 6.25,
      estimated_amount_cents: 93750,
    },
  ],
  recommendations: [
    "Envisagez de facturer le dossier Succession Dupont avant la fin du mois.",
    "Le taux de recouvrement est en baisse de 3% par rapport au mois precedent. Relancez les factures impayees.",
    "Les heures non facturees representent 15% du temps total. Objectif recommande : moins de 10%.",
    "Pensez a ajuster le taux horaire du dossier DOS-2025-049 pour reflechir la complexite du dossier.",
  ],
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatEUR(cents: number): string {
  return new Intl.NumberFormat("fr-BE", {
    style: "currency",
    currency: "EUR",
  }).format(cents / 100);
}

/* ------------------------------------------------------------------ */
/*  Custom Tooltip                                                     */
/* ------------------------------------------------------------------ */

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ dataKey: string; name: string; value: number; fill: string }>; label?: string }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="bg-white border border-neutral-200 rounded-lg shadow-lg px-4 py-3">
      <p className="text-sm font-semibold text-neutral-900 mb-1">{label}</p>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex items-center gap-2 text-sm">
          <span
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: p.fill }}
          />
          <span className="text-neutral-600">{p.name} :</span>
          <span className="font-medium text-neutral-900">
            {new Intl.NumberFormat("fr-BE", {
              style: "currency",
              currency: "EUR",
            }).format(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function BillingDashboard({
  accessToken,
  tenantId,
  onCreateInvoice,
}: BillingDashboardProps) {
  const [loading, setLoading] = useState(true);
  const [monthlyHours, setMonthlyHours] = useState(0);
  const [invoicedThisMonth, setInvoicedThisMonth] = useState(0);
  const [paidTotal, setPaidTotal] = useState(0);
  const [unbilledAmount, setUnbilledAmount] = useState(0);
  const [billingReport, setBillingReport] = useState<BillingReport | null>(
    null,
  );
  const [reportLoading, setReportLoading] = useState(true);

  // --- Fetch KPI data ---
  useEffect(() => {
    const now = new Date();
    const firstOfMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
    const today = now.toISOString().split("T")[0];

    Promise.all([
      apiFetch<{ items: TimeEntry[] }>(
        `/time-entries?date_from=${firstOfMonth}&date_to=${today}`,
        accessToken,
        { tenantId },
      ).catch(() => ({ items: [] as TimeEntry[] })),
      apiFetch<{ items: Invoice[] }>("/invoices", accessToken, {
        tenantId,
      }).catch(() => ({ items: [] as Invoice[] })),
    ])
      .then(([timeData, invoiceData]) => {
        // Monthly hours
        const totalMinutes = timeData.items.reduce(
          (sum, e) => sum + e.duration_minutes,
          0,
        );
        setMonthlyHours(Math.round((totalMinutes / 60) * 10) / 10);

        // Invoiced this month
        const thisMonthInvoices = invoiceData.items.filter((inv) => {
          const invDate = inv.created_at?.slice(0, 7);
          const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
          return invDate === currentMonth;
        });
        const invoicedTotal = thisMonthInvoices.reduce(
          (sum, inv) => sum + inv.total_cents,
          0,
        );
        setInvoicedThisMonth(invoicedTotal);

        // Paid
        const paidInvoices = invoiceData.items.filter(
          (inv) => inv.status === "paid",
        );
        const paidSum = paidInvoices.reduce(
          (sum, inv) => sum + inv.total_cents,
          0,
        );
        setPaidTotal(paidSum);

        // Unbilled estimate (approved but not invoiced time entries)
        const approvedEntries = timeData.items.filter(
          (e) => e.status === "approved",
        );
        const unbilledCents = approvedEntries.reduce((sum, e) => {
          const rate = e.hourly_rate_cents || 15000;
          return sum + Math.round((rate * e.duration_minutes) / 60);
        }, 0);
        setUnbilledAmount(unbilledCents);
      })
      .finally(() => setLoading(false));
  }, [accessToken, tenantId]);

  // --- Fetch AI billing report ---
  useEffect(() => {
    apiFetch<BillingReport>("/brain/billing/report", accessToken, { tenantId })
      .then((data) => setBillingReport(data))
      .catch(() => {
        // Fallback to mock data
        setBillingReport(MOCK_BILLING_REPORT);
      })
      .finally(() => setReportLoading(false));
  }, [accessToken, tenantId]);

  const report = billingReport || MOCK_BILLING_REPORT;

  /* ================================================================ */
  /*  RENDER                                                           */
  /* ================================================================ */

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Hours this month */}
        <Card className="bg-gradient-to-br from-accent-50 to-white border border-accent-100">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-xs font-medium text-neutral-600 uppercase tracking-wide mb-2">
                Heures ce mois
              </p>
              <p className="text-2xl font-bold text-accent">
                {loading ? "..." : `${monthlyHours}h`}
              </p>
            </div>
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-accent/10">
              <Clock className="w-5 h-5 text-accent" />
            </div>
          </div>
        </Card>

        {/* Invoiced this month */}
        <Card className="bg-gradient-to-br from-success-50 to-white border border-success-100">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-xs font-medium text-neutral-600 uppercase tracking-wide mb-2">
                CA Facture
              </p>
              <p className="text-2xl font-bold text-success">
                {loading ? "..." : formatEUR(invoicedThisMonth)}
              </p>
            </div>
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-success/10">
              <FileText className="w-5 h-5 text-success" />
            </div>
          </div>
        </Card>

        {/* Paid total */}
        <Card className="bg-gradient-to-br from-neutral-900 to-neutral-800 border border-neutral-700">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-xs font-medium text-neutral-400 uppercase tracking-wide mb-2">
                Encaissements
              </p>
              <p className="text-2xl font-bold text-white">
                {loading ? "..." : formatEUR(paidTotal)}
              </p>
            </div>
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-white/10">
              <CreditCard className="w-5 h-5 text-white" />
            </div>
          </div>
        </Card>

        {/* Unbilled */}
        <Card className="bg-gradient-to-br from-warning-50 to-white border border-warning-100">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-xs font-medium text-neutral-600 uppercase tracking-wide mb-2">
                A facturer
              </p>
              <p className="text-2xl font-bold text-warning-700">
                {loading ? "..." : formatEUR(unbilledAmount)}
              </p>
            </div>
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-warning/10">
              <AlertTriangle className="w-5 h-5 text-warning-600" />
            </div>
          </div>
        </Card>
      </div>

      {/* Revenue Chart */}
      <Card className="border border-neutral-200">
        <h3 className="text-base font-semibold text-neutral-900 mb-4">
          Chiffre d&apos;affaires mensuel
        </h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={MOCK_REVENUE_DATA}
              margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
            >
              <XAxis
                dataKey="month"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12, fill: "#6b7280" }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 12, fill: "#6b7280" }}
                tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip content={<ChartTooltip />} />
              <Bar
                dataKey="facture"
                name="Facture"
                fill="#6366f1"
                radius={[4, 4, 0, 0]}
                maxBarSize={40}
              />
              <Bar
                dataKey="encaisse"
                name="Encaisse"
                fill="#22c55e"
                radius={[4, 4, 0, 0]}
                maxBarSize={40}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="flex items-center justify-center gap-6 mt-2">
          <div className="flex items-center gap-2 text-sm text-neutral-600">
            <span className="w-3 h-3 rounded-sm bg-[#6366f1]" />
            Facture
          </div>
          <div className="flex items-center gap-2 text-sm text-neutral-600">
            <span className="w-3 h-3 rounded-sm bg-[#22c55e]" />
            Encaisse
          </div>
        </div>
      </Card>

      {/* AI Billing Intelligence */}
      <Card className="border border-neutral-200">
        <div className="flex items-center gap-3 mb-6">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-accent/10">
            <Brain className="w-5 h-5 text-accent" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-neutral-900">
              Intelligence facturation
            </h3>
            <p className="text-xs text-neutral-500">
              Analyse automatique de votre activite
            </p>
          </div>
          {reportLoading && (
            <Loader2 className="w-4 h-4 animate-spin text-accent ml-auto" />
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recovery rate gauge */}
          <div className="flex flex-col items-center justify-center p-4 bg-neutral-50 rounded-xl">
            <p className="text-xs font-medium text-neutral-600 uppercase tracking-wide mb-3">
              Taux de recouvrement
            </p>
            <div className="relative w-28 h-28">
              <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  fill="none"
                  stroke="#e5e7eb"
                  strokeWidth="10"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  fill="none"
                  stroke={
                    report.recovery_rate >= 80
                      ? "#22c55e"
                      : report.recovery_rate >= 60
                        ? "#eab308"
                        : "#ef4444"
                  }
                  strokeWidth="10"
                  strokeDasharray={`${(report.recovery_rate / 100) * 264} 264`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-2xl font-bold text-neutral-900">
                  {report.recovery_rate}%
                </span>
              </div>
            </div>
          </div>

          {/* Unbilled hours & amount */}
          <div className="p-4 bg-neutral-50 rounded-xl flex flex-col justify-center">
            <p className="text-xs font-medium text-neutral-600 uppercase tracking-wide mb-3">
              Heures non facturees
            </p>
            <p className="text-3xl font-bold text-warning-700 mb-1">
              {report.unbilled_hours}h
            </p>
            <p className="text-sm text-neutral-500">
              Montant estime : {formatEUR(report.unbilled_amount_cents)}
            </p>
          </div>

          {/* Anomalies */}
          <div className="p-4 bg-neutral-50 rounded-xl">
            <p className="text-xs font-medium text-neutral-600 uppercase tracking-wide mb-3">
              Alertes ({report.anomalies.length})
            </p>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {report.anomalies.map((a, i) => (
                <div key={i} className="flex items-start gap-2">
                  <Badge
                    variant={a.severity === "danger" ? "danger" : "warning"}
                    size="sm"
                    dot
                  >
                    {a.severity === "danger" ? "Critique" : "Attention"}
                  </Badge>
                  <p className="text-xs text-neutral-700 leading-relaxed">
                    {a.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Invoice suggestions */}
        {report.suggestions.length > 0 && (
          <div className="mt-6">
            <h4 className="text-sm font-semibold text-neutral-700 mb-3">
              Suggestions de facturation
            </h4>
            <div className="bg-white rounded-xl shadow-md border border-neutral-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-gradient-to-r from-neutral-50 to-neutral-100 border-b border-neutral-200">
                      <th className="text-left px-4 py-3 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                        Dossier
                      </th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                        Heures non facturees
                      </th>
                      <th className="text-right px-4 py-3 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                        Montant estime
                      </th>
                      <th className="px-4 py-3 text-xs font-semibold text-neutral-700 uppercase tracking-wider w-40">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100">
                    {report.suggestions.map((s) => (
                      <tr
                        key={s.case_id}
                        className="hover:bg-neutral-50/50 transition-all duration-200"
                      >
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-neutral-900">
                            {s.case_title}
                          </p>
                        </td>
                        <td className="px-4 py-3 text-sm font-medium text-neutral-900 text-right">
                          {s.unbilled_hours}h
                        </td>
                        <td className="px-4 py-3 text-sm font-semibold text-neutral-900 text-right">
                          {formatEUR(s.estimated_amount_cents)}
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() =>
                              onCreateInvoice && onCreateInvoice(s.case_id)
                            }
                            className="flex items-center gap-1 px-3 py-1.5 bg-accent text-white text-xs font-medium rounded-md hover:bg-accent/90 transition-colors"
                          >
                            <FileText className="w-3.5 h-3.5" />
                            Creer facture
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Recommendations */}
        {report.recommendations.length > 0 && (
          <div className="mt-6">
            <h4 className="text-sm font-semibold text-neutral-700 mb-3">
              Recommandations
            </h4>
            <div className="space-y-2">
              {report.recommendations.map((rec, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 p-3 bg-accent-50/30 border border-accent-100 rounded-lg"
                >
                  <TrendingUp className="w-4 h-4 text-accent mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-neutral-700">{rec}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Top Cases by Revenue */}
      <Card className="border border-neutral-200">
        <h3 className="text-base font-semibold text-neutral-900 mb-4">
          Top dossiers par chiffre d&apos;affaires
        </h3>
        <div className="bg-white rounded-xl shadow-md border border-neutral-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gradient-to-r from-neutral-50 to-neutral-100 border-b border-neutral-200">
                  <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                    Dossier
                  </th>
                  <th className="text-right px-6 py-4 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                    Heures
                  </th>
                  <th className="text-right px-6 py-4 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                    Facture
                  </th>
                  <th className="text-right px-6 py-4 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                    Encaisse
                  </th>
                  <th className="text-right px-6 py-4 text-xs font-semibold text-neutral-700 uppercase tracking-wider">
                    Taux recouvrement
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {MOCK_TOP_CASES.map((c) => {
                  const recoveryRate =
                    c.facture > 0
                      ? Math.round((c.encaisse / c.facture) * 100)
                      : 0;
                  return (
                    <tr
                      key={c.reference}
                      className="hover:bg-neutral-50/50 transition-all duration-200 group"
                    >
                      <td className="px-6 py-4">
                        <p className="text-sm font-semibold text-accent group-hover:text-accent-700 transition-colors">
                          {c.reference}
                        </p>
                        <p className="text-xs text-neutral-500 mt-0.5">
                          {c.title}
                        </p>
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-neutral-900 text-right">
                        {c.hours}h
                      </td>
                      <td className="px-6 py-4 text-sm font-semibold text-neutral-900 text-right">
                        {formatEUR(c.facture)}
                      </td>
                      <td className="px-6 py-4 text-sm font-semibold text-success text-right">
                        {formatEUR(c.encaisse)}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Badge
                          variant={
                            recoveryRate >= 90
                              ? "success"
                              : recoveryRate >= 70
                                ? "warning"
                                : "danger"
                          }
                          size="sm"
                        >
                          {recoveryRate}%
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </Card>
    </div>
  );
}
