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

      {/* Filter & View Section */}
      <div className="rounded-sm border border-[rgb(var(--color-border))] p-4 space-y-3" style={{ background: "rgb(var(--color-surface-raised))" }}>
        <div className="flex flex-col lg:flex-row lg:items-center gap-3">
          {/* Status Chips */}
          <div className="flex flex-wrap gap-1.5">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setStatusFilter(f.value)}
                className={`px-3.5 py-1.5 rounded-[2px] border text-xs font-semibold uppercase tracking-wide transition-colors duration-100 ${
                  statusFilter === f.value
                    ? "bg-[rgb(var(--color-primary))] text-white border-[rgb(var(--color-primary))] shadow-sm"
                    : "bg-white text-[rgb(var(--color-text-secondary))] border-[rgb(var(--color-border))] hover:bg-white hover:text-[rgb(var(--color-text-primary))] hover:border-[rgb(var(--color-primary))/30]"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="flex-1" />

          {/* Type Filter & Search */}
          <div className="flex flex-col sm:flex-row gap-2">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="input py-1.5 text-sm rounded-[2px]"
            >
              <option value="">Tous les types</option>
              {MATTER_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>

            <div className="relative flex-1 sm:flex-initial sm:w-60">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[rgb(var(--color-text-secondary))]" />
              <input
                type="text"
                placeholder="Chercher un dossier..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input pl-9 py-1.5 text-sm w-full rounded-[2px]"
              />
            </div>
          </div>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center justify-between pt-3 border-t border-[rgb(var(--color-border))]/50">
          <span className="label-overline">{filtered.length} résultats</span>
          <div className="flex gap-1 bg-[rgb(var(--color-border))]/30 rounded-[2px] p-0.5">
            <button
              onClick={() => setViewMode("table")}
              className={`p-1.5 rounded-[2px] transition-colors duration-100 ${
                viewMode === "table"
                  ? "bg-white text-[rgb(var(--color-primary))] shadow-sm"
                  : "text-[rgb(var(--color-text-secondary))] hover:text-[rgb(var(--color-text-primary))]"
              }`}
              title="Vue tableau"
            >
              <List className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded-[2px] transition-colors duration-100 ${
                viewMode === "grid"
                  ? "bg-white text-[rgb(var(--color-primary))] shadow-sm"
                  : "text-[rgb(var(--color-text-secondary))] hover:text-[rgb(var(--color-text-primary))]"
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
        <div className="bg-white rounded-sm overflow-hidden" style={{ boxShadow: "var(--shadow-card)" }}>
          <table className="w-full">
            <thead className="border-b-2 border-[rgb(var(--color-border))] sticky top-0" style={{ background: "rgb(var(--color-surface-raised))" }}>
              <tr>
                <th className="text-left px-6 py-3 label-overline">Référence</th>
                <th className="text-left px-6 py-3 label-overline">Titre</th>
                <th className="text-left px-6 py-3 label-overline">Statut</th>
                <th className="text-left px-6 py-3 label-overline">Type</th>
                <th className="text-left px-6 py-3 label-overline">Priorité</th>
                <th className="text-left px-6 py-3 label-overline">Client</th>
                <th className="text-left px-6 py-3 label-overline">Ouvert le</th>
                <th className="text-center px-4 py-3 label-overline">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => {
                const priority = c.metadata?.priority || "normal";
                const isTresUrgent = priority === "tres_urgent";
                const isUrgent = priority === "urgent";
                return (
                  <tr
                    key={c.id}
                    onClick={() => router.push(`/dashboard/cases/${c.id}`)}
                    className="border-b border-[rgb(var(--color-border))]/50 last:border-0 hover:bg-[rgb(var(--color-surface-raised))] transition-colors duration-100 cursor-pointer group"
                  >
                    <td className="px-6 py-3.5">
                      <span className="font-mono text-xs font-medium text-[rgb(var(--color-text-secondary))] tracking-tight">
                        {c.reference}
                      </span>
                    </td>
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-2">
                        {isTresUrgent && <span className="w-[3px] h-5 bg-danger-600 rounded-full flex-shrink-0" />}
                        {isUrgent && <span className="w-[3px] h-5 bg-warning-600 rounded-full flex-shrink-0" />}
                        <span className="text-sm font-semibold text-[rgb(var(--color-text-primary))] group-hover:text-accent transition-colors duration-100">
                          {c.title}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-3.5">
                      <Badge
                        variant={c.status === "open" ? "success" : c.status === "closed" ? "neutral" : c.status === "pending" ? "warning" : "accent"}
                        size="sm"
                      >
                        {statusLabels[c.status] || c.status}
                      </Badge>
                    </td>
                    <td className="px-6 py-3.5">
                      <Badge variant="neutral" size="sm">
                        {MATTER_TYPES.find((t) => t.value === c.matter_type)?.label || c.matter_type}
                      </Badge>
                    </td>
                    <td className="px-6 py-3.5">
                      {isTresUrgent ? (
                        <Badge variant="danger" filled size="sm">Très urgent</Badge>
                      ) : isUrgent ? (
                        <Badge variant="warning" size="sm">Urgent</Badge>
                      ) : (
                        <span className="text-xs text-[rgb(var(--color-text-secondary))]">Normal</span>
                      )}
                    </td>
                    <td className="px-6 py-3.5">
                      <span className="text-sm text-[rgb(var(--color-text-secondary))] truncate max-w-[140px] block">
                        {c.metadata?.parties?.clients?.[0]?.name || "—"}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-sm text-[rgb(var(--color-text-secondary))]">
                      {new Date(c.opened_at).toLocaleDateString("fr-BE")}
                    </td>
                    <td className="px-4 py-3.5 text-center">
                      <ChevronRight className="w-4 h-4 text-[rgb(var(--color-text-secondary))] opacity-0 group-hover:opacity-100 group-hover:text-accent transition-all duration-100 mx-auto" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        /* Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((c) => {
            const priority = c.metadata?.priority || "normal";
            const isTresUrgent = priority === "tres_urgent";
            const isUrgent = priority === "urgent";
            return (
              <Card
                key={c.id}
                hover
                onClick={() => router.push(`/dashboard/cases/${c.id}`)}
                variant={isTresUrgent || isUrgent ? "accent-top" : "default"}
                header={
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <span className="label-overline block mb-1">{c.reference}</span>
                      <h3 className="text-base font-semibold text-[rgb(var(--color-text-primary))] line-clamp-2 leading-snug">
                        {c.title}
                      </h3>
                    </div>
                    <ChevronRight className="w-4 h-4 text-[rgb(var(--color-text-secondary))] flex-shrink-0 mt-0.5" />
                  </div>
                }
                className="group"
              >
                <div className="space-y-2.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge
                      variant={c.status === "open" ? "success" : c.status === "closed" ? "neutral" : c.status === "pending" ? "warning" : "accent"}
                      size="sm"
                    >
                      {statusLabels[c.status] || c.status}
                    </Badge>
                    <Badge variant="neutral" size="sm">
                      {MATTER_TYPES.find((t) => t.value === c.matter_type)?.label || c.matter_type}
                    </Badge>
                    {isTresUrgent && <Badge variant="danger" filled size="sm">Très urgent</Badge>}
                    {isUrgent && !isTresUrgent && <Badge variant="warning" size="sm">Urgent</Badge>}
                  </div>

                  {c.metadata?.parties?.clients?.[0]?.name && (
                    <div className="text-sm text-[rgb(var(--color-text-secondary))]">
                      <span className="label-overline mr-1.5">Client</span>
                      {c.metadata.parties.clients[0].name}
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-2 border-t border-[rgb(var(--color-border))]/50 text-xs text-[rgb(var(--color-text-secondary))]">
                    <span>{new Date(c.opened_at).toLocaleDateString("fr-BE")}</span>
                    {c.metadata?.key_dates?.next_hearing && (
                      <span className="flex items-center gap-1 text-accent-600">
                        <Clock className="w-3 h-3" />
                        {new Date(c.metadata.key_dates.next_hearing).toLocaleDateString("fr-BE")}
                      </span>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
