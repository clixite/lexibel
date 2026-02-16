"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { Plus, Loader2, Search, Folder } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface Case {
  id: string;
  reference: string;
  title: string;
  status: string;
  matter_type: string;
  opened_at: string;
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
  { label: "Ferm\u00e9", value: "closed" },
  { label: "En attente", value: "pending" },
];

const statusStyles: Record<string, string> = {
  open: "bg-success-50 text-success-700",
  closed: "bg-neutral-100 text-neutral-600",
  pending: "bg-warning-50 text-warning-700",
  archived: "bg-neutral-100 text-neutral-500",
};

const statusLabels: Record<string, string> = {
  open: "Ouvert",
  closed: "Ferm\u00e9",
  pending: "En attente",
  archived: "Archiv\u00e9",
};

export default function CasesPage() {
  const { data: session } = useSession();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    const token = (session?.user as any)?.accessToken;
    if (!token) return;

    apiFetch<CaseListResponse>("/cases", token)
      .then((data) => setCases(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [session]);

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
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-neutral-900">Dossiers</h1>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-accent-50 text-accent-700">
            {cases.length}
          </span>
        </div>
        <button className="btn-primary flex items-center gap-2">
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

      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-neutral-200">
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                R&eacute;f&eacute;rence
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
                <td colSpan={5} className="px-6 py-16 text-center">
                  <Folder className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
                  <p className="text-neutral-500 font-medium">
                    Aucun dossier trouv&eacute;
                  </p>
                  <p className="text-neutral-400 text-sm mt-1">
                    {searchQuery || statusFilter
                      ? "Essayez de modifier vos filtres."
                      : "Cr\u00e9ez votre premier dossier pour commencer."}
                  </p>
                  {!searchQuery && !statusFilter && (
                    <button className="btn-primary mt-4">
                      <Plus className="w-4 h-4 inline mr-1.5" />
                      Nouveau dossier
                    </button>
                  )}
                </td>
              </tr>
            ) : (
              filtered.map((c) => (
                <tr
                  key={c.id}
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
                      {c.matter_type}
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
