"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Loader2, Search, Folder, X, Check } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, Badge, Modal } from "@/components/ui";

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
];

function generateReference(): string {
  const year = new Date().getFullYear();
  const num = String(Math.floor(Math.random() * 999) + 1).padStart(3, "0");
  return `DOS-${year}-${num}`;
}

export default function CasesPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  const [form, setForm] = useState({
    reference: generateReference(),
    title: "",
    matter_type: "general",
    description: "",
    status: "open",
  });

  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;
  const userId = (session?.user as any)?.id;

  const loadCases = () => {
    if (!token) return;
    setLoading(true);
    apiFetch<CaseListResponse>("/cases", token, { tenantId })
      .then((data) => setCases(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  const handleCreate = async () => {
    if (!token || !form.title.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await apiFetch("/cases", token, {
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
      setSuccess("Dossier créé avec succès");
      setShowModal(false);
      setForm({
        reference: generateReference(),
        title: "",
        matter_type: "general",
        description: "",
        status: "open",
      });
      loadCases();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const filtered = cases.filter((c) => {
    if (statusFilter && c.status !== statusFilter) return false;
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
    <div>
      {/* Success toast */}
      {success && (
        <div className="fixed top-4 right-4 z-50 bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-md text-sm flex items-center gap-2 shadow-lg animate-in fade-in">
          <Check className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-neutral-900">Dossiers</h1>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-accent-50 text-accent-700">
            {cases.length}
          </span>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nouveau dossier
        </button>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="flex gap-1 bg-neutral-100 rounded-md p-1">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 ${
                statusFilter === f.value
                  ? "bg-white text-neutral-900 shadow-subtle"
                  : "text-neutral-500 hover:text-neutral-700"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Rechercher un dossier..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-9"
          />
        </div>
      </div>


      {/* Create Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Nouveau dossier"
        footer={
          <div className="flex justify-end gap-3">
            <button
              onClick={() => setShowModal(false)}
              className="px-4 py-2 text-sm font-medium text-neutral-600 bg-neutral-100 rounded-md hover:bg-neutral-200 transition-colors"
            >
              Annuler
            </button>
            <button
              onClick={handleCreate}
              disabled={creating || !form.title.trim()}
              className="btn-primary flex items-center gap-2 disabled:opacity-50"
            >
              {creating && <Loader2 className="w-4 h-4 animate-spin" />}
              Créer le dossier
            </button>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Référence
              </label>
              <input
                type="text"
                value={form.reference}
                onChange={(e) =>
                  setForm((f) => ({ ...f, reference: e.target.value }))
                }
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Type
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
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Titre
            </label>
            <input
              type="text"
              value={form.title}
              onChange={(e) =>
                setForm((f) => ({ ...f, title: e.target.value }))
              }
              placeholder="Ex: Dupont c/ SA Immobel"
              className="input"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Description
            </label>
            <textarea
              value={form.description}
              onChange={(e) =>
                setForm((f) => ({ ...f, description: e.target.value }))
              }
              placeholder="Description du dossier..."
              className="input"
              rows={3}
            />
          </div>
        </div>
      </Modal>

      {/* Table */}
      <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-neutral-200">
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Référence
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Titre
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Statut
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Type
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Ouvert le
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  <div className="px-6 py-16 text-center">
                    <EmptyState title="Aucun dossier trouvé" />
                    {!searchQuery && !statusFilter && (
                      <button
                        onClick={() => setShowModal(true)}
                        className="btn-primary mt-4"
                      >
                        <Plus className="w-4 h-4 inline mr-1.5" />
                        Nouveau dossier
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => router.push(`/dashboard/cases/${c.id}`)}
                  className="hover:bg-neutral-50 transition-colors duration-150 cursor-pointer"
                >
                  <td className="px-6 py-4 text-sm font-medium text-accent">
                    {c.reference}
                  </td>
                  <td className="px-6 py-4 text-sm text-neutral-900">
                    {c.title}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        statusStyles[c.status] ||
                        "bg-neutral-100 text-neutral-600"
                      }`}
                    >
                      {statusLabels[c.status] || c.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-neutral-100 text-neutral-600">
                      {MATTER_TYPES.find((t) => t.value === c.matter_type)
                        ?.label || c.matter_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-neutral-500">
                    {new Date(c.opened_at).toLocaleDateString("fr-BE")}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
