"use client";

import { useAuth } from "@/lib/useAuth";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Search, Grid3x3, List, Check, ChevronRight, AlertTriangle, Clock } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, Badge, Button, Card } from "@/components/ui";

interface Case {
  id: string;
  reference: string;
  title: string;
  status: string;
  matter_type: string;
  opened_at: string;
  responsible_user_id: string;
  jurisdiction: string | null;
  court_reference: string | null;
  metadata: {
    description?: string;
    priority?: string;
    sub_type?: string;
    billing?: { type?: string };
    parties?: { clients?: { name: string }[]; adverse?: { name: string }[] };
    key_dates?: { next_hearing?: string; prescription?: string };
    legal_aid?: { enabled?: boolean };
    [key: string]: unknown;
  };
}

interface CaseListResponse {
  items: Case[];
  total: number;
  page: number;
  per_page: number;
}

const STATUS_FILTERS = [
  { label: "Tous", value: "" },
  { label: "Ouvert", value: "open" },
  { label: "Fermé", value: "closed" },
  { label: "En attente", value: "pending" },
];

const statusStyles: Record<string, string> = {
  open: "bg-success-50 text-success-700",
  in_progress: "bg-accent-50 text-accent-700",
  closed: "bg-neutral-100 text-neutral-600",
  pending: "bg-warning-50 text-warning-700",
  archived: "bg-neutral-100 text-neutral-500",
};

const statusLabels: Record<string, string> = {
  open: "Ouvert",
  in_progress: "En cours",
  closed: "Fermé",
  pending: "En attente",
  archived: "Archivé",
};

const MATTER_TYPES = [
  { value: "general", label: "Général" },
  { value: "civil", label: "Civil" },
  { value: "penal", label: "Pénal" },
  { value: "commercial", label: "Commercial" },
  { value: "social", label: "Social" },
  { value: "fiscal", label: "Fiscal" },
  { value: "family", label: "Familial" },
  { value: "administrative", label: "Administratif" },
  { value: "immobilier", label: "Immobilier" },
  { value: "construction", label: "Construction" },
  { value: "societes", label: "Sociétés" },
  { value: "environnement", label: "Environnement" },
  { value: "ip", label: "Propriété intellectuelle" },
];

const PRIORITY_STYLES: Record<string, string> = {
  normal: "bg-neutral-100 text-neutral-600",
  urgent: "bg-warning-50 text-warning-700",
  tres_urgent: "bg-red-50 text-red-700",
};

const PRIORITY_LABELS: Record<string, string> = {
  normal: "Normal",
  urgent: "Urgent",
  tres_urgent: "Très urgent",
};

export default function CasesPage() {
  const { accessToken, tenantId, userId } = useAuth();
  const router = useRouter();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [success, setSuccess] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"table" | "grid">("table");

  const loadCases = () => {
    if (!accessToken) return;
    setLoading(true);
    apiFetch<CaseListResponse>("/cases", accessToken, { tenantId })
      .then((data) => setCases(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, tenantId]);

  const filtered = cases.filter((c) => {
    if (statusFilter && c.status !== statusFilter) return false;
    if (typeFilter && c.matter_type !== typeFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        c.title.toLowerCase().includes(q) ||
        c.reference.toLowerCase().includes(q)
      );
    }
    return true;
  });

  if (loading) {
    return <LoadingSkeleton variant="table" />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => window.location.reload()} />;
  }

  return (
    <div className="space-y-6">
      {/* Success toast */}
      {success && (
        <div className="fixed top-4 right-4 z-50 bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2 shadow-lg animate-in fade-in">
          <Check className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* Header Section - Corporate */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-bold text-neutral-900 mb-2">
            Dossiers
          </h1>
          <p className="text-neutral-600 text-sm">
            Gérez et suivez tous vos dossiers clients
          </p>
        </div>
        <Button
          variant="primary"
          size="lg"
          icon={<Plus className="w-5 h-5" />}
          onClick={() => router.push("/dashboard/cases/new")}
        >
          Nouveau dossier
        </Button>
      </div>

      {/* Filter & View Section - Corporate */}
      <div className="bg-white rounded shadow-sm border border-neutral-200 p-6 space-y-4">
        {/* Inline Filters */}
        <div className="flex flex-col lg:flex-row lg:items-center gap-4">
          {/* Status Chips - Corporate */}
          <div className="flex flex-wrap gap-2">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setStatusFilter(f.value)}
                className={`px-4 py-2 rounded border text-sm font-medium transition-colors duration-150 ${
                  statusFilter === f.value
                    ? "bg-primary text-white border-primary"
                    : "bg-white text-neutral-600 border-neutral-300 hover:bg-neutral-50"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Type Filter & Search */}
          <div className="flex flex-col sm:flex-row gap-3">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="input py-2 text-sm"
            >
              <option value="">Tous les types</option>
              {MATTER_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>

            <div className="relative flex-1 sm:flex-initial sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
              <input
                type="text"
                placeholder="Chercher un dossier..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input pl-10 py-2 text-sm w-full"
              />
            </div>
          </div>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center justify-between pt-4 border-t border-neutral-100">
          <span className="text-sm text-neutral-500">
            {filtered.length} résultats
          </span>
          <div className="flex gap-2 bg-neutral-100 rounded p-1">
            <button
              onClick={() => setViewMode("table")}
              className={`p-2 rounded transition-colors duration-150 ${
                viewMode === "table"
                  ? "bg-white text-primary shadow-sm"
                  : "text-neutral-500 hover:text-neutral-700"
              }`}
              title="Vue tableau"
            >
              <List className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode("grid")}
              className={`p-2 rounded transition-colors duration-150 ${
                viewMode === "grid"
                  ? "bg-white text-primary shadow-sm"
                  : "text-neutral-500 hover:text-neutral-700"
              }`}
              title="Vue grille"
            >
              <Grid3x3 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>


      {/* Content Display */}
      {filtered.length === 0 ? (
        <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 p-12 text-center">
          <EmptyState title="Aucun dossier trouvé" />
          {!searchQuery && !statusFilter && !typeFilter && (
            <Button
              variant="primary"
              size="lg"
              icon={<Plus className="w-5 h-5" />}
              onClick={() => router.push("/dashboard/cases/new")}
              className="mt-6"
            >
              Créer votre premier dossier
            </Button>
          )}
        </div>
      ) : viewMode === "table" ? (
        /* Table View */
        <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 overflow-hidden">
          <table className="w-full">
            <thead className="bg-neutral-50 border-b border-neutral-200">
              <tr>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Référence
                </th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Titre
                </th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Statut
                </th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Type
                </th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Priorité
                </th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Client
                </th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Ouvert le
                </th>
                <th className="text-center px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {filtered.map((c) => (
                <tr
                  key={c.id}
                  className="hover:bg-neutral-50 transition-all duration-150 cursor-pointer group"
                >
                  <td className="px-6 py-4">
                    <span className="text-sm font-semibold text-accent group-hover:text-accent-700">
                      {c.reference}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm font-medium text-neutral-900 group-hover:text-accent">
                      {c.title}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <Badge
                      variant={
                        c.status === "open"
                          ? "success"
                          : c.status === "closed"
                          ? "neutral"
                          : c.status === "pending"
                          ? "warning"
                          : "accent"
                      }
                      size="sm"
                    >
                      {statusLabels[c.status] || c.status}
                    </Badge>
                  </td>
                  <td className="px-6 py-4">
                    <Badge variant="neutral" size="sm">
                      {MATTER_TYPES.find((t) => t.value === c.matter_type)
                        ?.label || c.matter_type}
                    </Badge>
                  </td>
                  <td className="px-6 py-4">
                    {c.metadata?.priority && c.metadata.priority !== "normal" ? (
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${PRIORITY_STYLES[c.metadata.priority] || PRIORITY_STYLES.normal}`}>
                        {c.metadata.priority === "tres_urgent" && <AlertTriangle className="w-3 h-3" />}
                        {PRIORITY_LABELS[c.metadata.priority] || c.metadata.priority}
                      </span>
                    ) : (
                      <span className="text-xs text-neutral-400">Normal</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-sm text-neutral-600 truncate max-w-[150px] block">
                      {c.metadata?.parties?.clients?.[0]?.name || "-"}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-neutral-500">
                    {new Date(c.opened_at).toLocaleDateString("fr-BE")}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <button
                      onClick={() => router.push(`/dashboard/cases/${c.id}`)}
                      className="p-2 rounded-lg hover:bg-accent hover:text-white transition-all opacity-0 group-hover:opacity-100"
                      title="Ouvrir le dossier"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((c) => (
            <Card
              key={c.id}
              hover
              onClick={() => router.push(`/dashboard/cases/${c.id}`)}
              header={
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-xs text-neutral-500 uppercase tracking-wider font-semibold mb-1">
                      {c.reference}
                    </p>
                    <h3 className="text-lg font-semibold text-neutral-900 line-clamp-2">
                      {c.title}
                    </h3>
                  </div>
                  <ChevronRight className="w-5 h-5 text-neutral-300 group-hover:text-accent transition-colors" />
                </div>
              }
              className="group"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge
                    variant={
                      c.status === "open"
                        ? "success"
                        : c.status === "closed"
                        ? "neutral"
                        : c.status === "pending"
                        ? "warning"
                        : "accent"
                    }
                  >
                    {statusLabels[c.status] || c.status}
                  </Badge>
                  <Badge variant="neutral">
                    {MATTER_TYPES.find((t) => t.value === c.matter_type)
                      ?.label || c.matter_type}
                  </Badge>
                </div>
                {c.metadata?.priority && c.metadata.priority !== "normal" && (
                  <div>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${PRIORITY_STYLES[c.metadata.priority] || ""}`}>
                      {c.metadata.priority === "tres_urgent" && <AlertTriangle className="w-3 h-3" />}
                      {PRIORITY_LABELS[c.metadata.priority] || c.metadata.priority}
                    </span>
                  </div>
                )}
                {c.metadata?.parties?.clients?.[0]?.name && (
                  <div className="text-sm text-neutral-600">
                    <span className="text-neutral-400">Client : </span>
                    {c.metadata.parties.clients[0].name}
                  </div>
                )}
                {c.jurisdiction && (
                  <div className="text-xs text-neutral-500 truncate">
                    {c.jurisdiction}
                  </div>
                )}
                <div className="flex items-center justify-between text-sm text-neutral-500 pt-1 border-t border-neutral-100">
                  <span>
                    {new Date(c.opened_at).toLocaleDateString("fr-BE")}
                  </span>
                  {c.metadata?.key_dates?.next_hearing && (
                    <span className="flex items-center gap-1 text-xs text-accent-600">
                      <Clock className="w-3 h-3" />
                      {new Date(c.metadata.key_dates.next_hearing).toLocaleDateString("fr-BE")}
                    </span>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
