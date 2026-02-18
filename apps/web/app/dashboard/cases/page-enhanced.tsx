"use client";

import { useAuth } from "@/lib/useAuth";
import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Plus, Search, Grid3x3, List, ChevronRight, Archive, Trash2 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, Badge, Modal, Button, Card } from "@/components/ui";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { toast } from "@/components/ToastContainer";
import BulkActionBar from "@/components/BulkActionBar";

interface Case {
  id: string;
  reference: string;
  title: string;
  status: string;
  matter_type: string;
  opened_at: string;
  responsible_user_id: string;
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
];

function generateReference(): string {
  const year = new Date().getFullYear();
  const num = String(Math.floor(Math.random() * 999) + 1).padStart(3, "0");
  return `DOS-${year}-${num}`;
}

export default function CasesPage() {
  const { accessToken, tenantId, userId } = useAuth();
  const router = useRouter();
  const searchInputRef = useRef<HTMLInputElement>(null);

  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [viewMode, setViewMode] = useState<"table" | "grid">("table");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const [form, setForm] = useState({
    reference: generateReference(),
    title: "",
    matter_type: "general",
    description: "",
    status: "open",
  });

  // Keyboard shortcuts
  useKeyboardShortcuts({
    n: () => setShowModal(true),
    "/": () => searchInputRef.current?.focus(),
  });

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

  const handleCreate = async () => {
    if (!accessToken || !form.title.trim()) return;
    setCreating(true);
    setError(null);

    // Optimistic update
    const tempId = `temp-${Date.now()}`;
    const tempCase: Case = {
      id: tempId,
      reference: form.reference,
      title: form.title,
      matter_type: form.matter_type,
      status: form.status,
      responsible_user_id: userId,
      opened_at: new Date().toISOString(),
    };
    setCases([tempCase, ...cases]);

    try {
      const result = await apiFetch<Case>("/cases", accessToken, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          reference: form.reference,
          title: form.title,
          matter_type: form.matter_type,
          status: form.status,
          responsible_user_id: userId,
          metadata: form.description ? { description: form.description } : {},
        }),
      });

      // Replace temp with real
      setCases(cases.map((c) => (c.id === tempId ? result : c)));
      toast.success("Dossier créé avec succès");
      setShowModal(false);
      setForm({
        reference: generateReference(),
        title: "",
        matter_type: "general",
        description: "",
        status: "open",
      });
    } catch (err: any) {
      // Rollback
      setCases(cases.filter((c) => c.id !== tempId));
      toast.error(err.message || "Erreur lors de la création du dossier");
    } finally {
      setCreating(false);
    }
  };

  const handleBulkArchive = async () => {
    if (selectedIds.size === 0) return;
    toast.info(`Archivage de ${selectedIds.size} dossier(s)...`);
    // TODO: Implement bulk archive API call
    setTimeout(() => {
      toast.success(`${selectedIds.size} dossier(s) archivé(s)`);
      setSelectedIds(new Set());
    }, 1000);
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    const confirmed = confirm(
      `Êtes-vous sûr de vouloir supprimer ${selectedIds.size} dossier(s) ?`
    );
    if (!confirmed) return;

    toast.info(`Suppression de ${selectedIds.size} dossier(s)...`);
    // TODO: Implement bulk delete API call
    setTimeout(() => {
      toast.success(`${selectedIds.size} dossier(s) supprimé(s)`);
      setSelectedIds(new Set());
    }, 1000);
  };

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
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-bold text-neutral-900 mb-2">
            Dossiers
          </h1>
          <p className="text-neutral-600 text-sm">
            Gérez et suivez tous vos dossiers clients
          </p>
        </div>
        <div className="flex items-center gap-3">
          <kbd className="px-3 py-1.5 text-xs bg-neutral-100 text-neutral-600 rounded font-mono border border-neutral-200">
            N
          </kbd>
          <Button
            variant="primary"
            size="lg"
            icon={<Plus className="w-5 h-5" />}
            onClick={() => setShowModal(true)}
          >
            Nouveau dossier
          </Button>
        </div>
      </div>

      {/* Filter & View Section */}
      <div className="bg-white rounded shadow-sm border border-neutral-200 p-6 space-y-4">
        {/* Inline Filters */}
        <div className="flex flex-col lg:flex-row lg:items-center gap-4">
          {/* Status Chips */}
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
                ref={searchInputRef}
                type="text"
                placeholder="Chercher un dossier... (/)"
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
            {filtered.length} résultat{filtered.length > 1 ? "s" : ""}
            {selectedIds.size > 0 && ` • ${selectedIds.size} sélectionné(s)`}
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

      {/* Bulk Action Bar */}
      <BulkActionBar
        selectedCount={selectedIds.size}
        onArchive={handleBulkArchive}
        onDelete={handleBulkDelete}
        onCancel={() => setSelectedIds(new Set())}
      />

      {/* Create Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Créer un nouveau dossier"
        size="lg"
        footer={
          <div className="flex justify-end gap-3">
            <Button
              variant="secondary"
              size="md"
              onClick={() => setShowModal(false)}
            >
              Annuler
            </Button>
            <Button
              variant="primary"
              size="md"
              loading={creating}
              disabled={creating || !form.title.trim()}
              onClick={handleCreate}
            >
              Créer le dossier
            </Button>
          </div>
        }
      >
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Référence
              </label>
              <input
                type="text"
                value={form.reference}
                onChange={(e) =>
                  setForm((f) => ({ ...f, reference: e.target.value }))
                }
                placeholder="DOS-2026-001"
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Type de dossier
              </label>
              <select
                value={form.matter_type}
                onChange={(e) =>
                  setForm((f) => ({ ...f, matter_type: e.target.value }))
                }
                className="input"
              >
                {MATTER_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-semibold text-neutral-900 mb-2">
              Titre du dossier
            </label>
            <input
              type="text"
              value={form.title}
              onChange={(e) =>
                setForm((f) => ({ ...f, title: e.target.value }))
              }
              placeholder="Ex: Dupont c/ SA Immobel"
              className="input"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-neutral-900 mb-2">
              Description (optionnel)
            </label>
            <textarea
              value={form.description}
              onChange={(e) =>
                setForm((f) => ({ ...f, description: e.target.value }))
              }
              placeholder="Décrivez le contexte et les détails du dossier..."
              className="input"
              rows={3}
            />
          </div>
        </div>
      </Modal>

      {/* Content Display */}
      {filtered.length === 0 ? (
        <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 p-12">
          <EmptyState
            title="Aucun dossier trouvé"
            description={
              searchQuery || statusFilter || typeFilter
                ? "Essayez d'ajuster vos filtres de recherche"
                : "Créez votre premier dossier pour commencer"
            }
            action={
              !searchQuery && !statusFilter && !typeFilter
                ? {
                    label: "Créer votre premier dossier",
                    onClick: () => setShowModal(true),
                    shortcut: "N",
                  }
                : undefined
            }
            suggestions={
              searchQuery || statusFilter || typeFilter
                ? [
                    {
                      label: "Réinitialiser tous les filtres",
                      onClick: () => {
                        setSearchQuery("");
                        setStatusFilter("");
                        setTypeFilter("");
                      },
                    },
                  ]
                : undefined
            }
          />
        </div>
      ) : viewMode === "table" ? (
        /* Table View with Selection */
        <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 overflow-hidden">
          <table className="w-full">
            <thead className="bg-neutral-50 border-b border-neutral-200">
              <tr>
                <th className="px-4 py-4 w-12">
                  <input
                    type="checkbox"
                    checked={filtered.length > 0 && selectedIds.size === filtered.length}
                    onChange={() => {
                      if (selectedIds.size === filtered.length) {
                        setSelectedIds(new Set());
                      } else {
                        setSelectedIds(new Set(filtered.map((c) => c.id)));
                      }
                    }}
                    className="rounded border-neutral-300 text-primary focus:ring-primary"
                  />
                </th>
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
                  Ouvert le
                </th>
                <th className="text-center px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {filtered.map((c) => {
                const isSelected = selectedIds.has(c.id);
                return (
                  <tr
                    key={c.id}
                    className={`transition-all duration-150 cursor-pointer group ${
                      isSelected ? "bg-primary/5" : "hover:bg-neutral-50"
                    }`}
                  >
                    <td
                      className="px-4 py-4"
                      onClick={(e) => {
                        e.stopPropagation();
                        const newSet = new Set(selectedIds);
                        if (newSet.has(c.id)) {
                          newSet.delete(c.id);
                        } else {
                          newSet.add(c.id);
                        }
                        setSelectedIds(newSet);
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {}}
                        className="rounded border-neutral-300 text-primary focus:ring-primary"
                      />
                    </td>
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
                );
              })}
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
              <div className="space-y-4">
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
                <div className="text-sm text-neutral-500">
                  Ouvert le{" "}
                  <span className="font-medium text-neutral-700">
                    {new Date(c.opened_at).toLocaleDateString("fr-BE")}
                  </span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
