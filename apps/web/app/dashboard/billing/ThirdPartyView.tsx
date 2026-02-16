"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { Plus, Loader2, X } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface ThirdPartyEntry {
  id: string;
  entry_type: string;
  amount_cents: number;
  reference: string;
  entry_date: string;
  case_id: string;
}

interface Balance {
  deposits: number;
  withdrawals: number;
  interest: number;
  balance: number;
}

interface CaseOption {
  id: string;
  reference: string;
  title: string;
}

function formatCents(cents: number): string {
  return (cents / 100).toFixed(2) + " \u20ac";
}

const TYPE_COLORS: Record<string, string> = {
  deposit: "text-success",
  withdrawal: "text-danger",
  interest: "text-accent",
};

const TYPE_LABELS: Record<string, string> = {
  deposit: "D\u00e9p\u00f4t",
  withdrawal: "Retrait",
  interest: "Int\u00e9r\u00eats",
};

export default function ThirdPartyView() {
  const { data: session } = useSession();
  const [balance, setBalance] = useState<Balance | null>(null);
  const [entries, setEntries] = useState<ThirdPartyEntry[]>([]);
  const [cases, setCases] = useState<CaseOption[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [loading, setLoading] = useState(true);
  const [entriesLoading, setEntriesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    case_id: "",
    entry_type: "deposit",
    amount_cents: 0,
    reference: "",
    entry_date: new Date().toISOString().split("T")[0],
  });

  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;

  useEffect(() => {
    if (!token) return;
    apiFetch<{ items: CaseOption[] }>("/cases", token, { tenantId })
      .then((data) => setCases(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token, tenantId]);

  const loadEntries = async (caseId: string) => {
    if (!token || !caseId) return;
    setEntriesLoading(true);
    setError(null);
    try {
      const [balanceData, entriesData] = await Promise.all([
        apiFetch<Balance>(`/third-party-entries/balance?case_id=${caseId}`, token, { tenantId }),
        apiFetch<{ items: ThirdPartyEntry[] }>(`/third-party-entries?case_id=${caseId}`, token, { tenantId }),
      ]);
      setBalance(balanceData);
      setEntries(entriesData.items);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setEntriesLoading(false);
    }
  };

  const handleCaseChange = (caseId: string) => {
    setSelectedCaseId(caseId);
    if (caseId) {
      loadEntries(caseId);
    } else {
      setBalance(null);
      setEntries([]);
    }
  };

  const handleSubmit = async () => {
    if (!token || !formData.case_id || formData.amount_cents <= 0) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiFetch("/third-party-entries", token, {
        tenantId,
        method: "POST",
        body: JSON.stringify(formData),
      });
      setShowForm(false);
      setFormData({
        case_id: selectedCaseId,
        entry_type: "deposit",
        amount_cents: 0,
        reference: "",
        entry_date: new Date().toISOString().split("T")[0],
      });
      if (selectedCaseId) {
        await loadEntries(selectedCaseId);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  return (
    <div>
      {/* Case selector */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-neutral-700 mb-1">Dossier</label>
        <select
          value={selectedCaseId}
          onChange={(e) => handleCaseChange(e.target.value)}
          className="input max-w-md"
        >
          <option value="">S&eacute;lectionner un dossier...</option>
          {cases.map((c) => (
            <option key={c.id} value={c.id}>
              {c.reference} &mdash; {c.title}
            </option>
          ))}
        </select>
      </div>

      {/* Balance card */}
      {balance && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="card">
            <p className="text-sm text-neutral-500">D&eacute;p&ocirc;ts</p>
            <p className="text-xl font-bold text-success">{formatCents(balance.deposits)}</p>
          </div>
          <div className="card">
            <p className="text-sm text-neutral-500">Retraits</p>
            <p className="text-xl font-bold text-danger">{formatCents(balance.withdrawals)}</p>
          </div>
          <div className="card">
            <p className="text-sm text-neutral-500">Int&eacute;r&ecirc;ts</p>
            <p className="text-xl font-bold text-accent">{formatCents(balance.interest)}</p>
          </div>
          <div className="card">
            <p className="text-sm text-neutral-500">Solde</p>
            <p className="text-xl font-bold text-neutral-900">{formatCents(balance.balance)}</p>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-neutral-500">
          {selectedCaseId
            ? `${entries.length} \u00e9criture(s) pour ce dossier.`
            : "S\u00e9lectionnez un dossier pour voir les mouvements du compte de tiers."}
        </p>
        <button
          onClick={() => {
            setFormData((f) => ({ ...f, case_id: selectedCaseId }));
            setShowForm(true);
          }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nouvelle &eacute;criture
        </button>
      </div>

      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-4 text-sm">{error}</div>
      )}

      {/* Form */}
      {showForm && (
        <div className="card mb-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-neutral-900">Nouvelle &eacute;criture</h3>
            <button onClick={() => setShowForm(false)} className="text-neutral-400 hover:text-neutral-600">
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Dossier</label>
              <select
                value={formData.case_id}
                onChange={(e) => setFormData((f) => ({ ...f, case_id: e.target.value }))}
                className="input"
              >
                <option value="">S&eacute;lectionner un dossier...</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.reference} &mdash; {c.title}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Type</label>
              <select
                value={formData.entry_type}
                onChange={(e) => setFormData((f) => ({ ...f, entry_type: e.target.value }))}
                className="input"
              >
                <option value="deposit">D&eacute;p&ocirc;t</option>
                <option value="withdrawal">Retrait</option>
                <option value="interest">Int&eacute;r&ecirc;ts</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Montant (&euro;)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={(formData.amount_cents / 100).toFixed(2)}
                onChange={(e) => setFormData((f) => ({ ...f, amount_cents: Math.round(parseFloat(e.target.value) * 100) || 0 }))}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">R&eacute;f&eacute;rence</label>
              <input
                type="text"
                value={formData.reference}
                onChange={(e) => setFormData((f) => ({ ...f, reference: e.target.value }))}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">Date</label>
              <input
                type="date"
                value={formData.entry_date}
                onChange={(e) => setFormData((f) => ({ ...f, entry_date: e.target.value }))}
                className="input"
              />
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <button
              onClick={handleSubmit}
              disabled={!formData.case_id || formData.amount_cents <= 0 || submitting}
              className="btn-primary disabled:opacity-50"
            >
              {submitting ? "Enregistrement..." : "Enregistrer"}
            </button>
          </div>
        </div>
      )}

      {/* Entries table */}
      {entriesLoading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-neutral-200">
                <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">Date</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">Type</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">R&eacute;f&eacute;rence</th>
                <th className="text-right px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">Montant</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {entries.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-sm text-neutral-400">
                    {selectedCaseId
                      ? "Aucune \u00e9criture trouv\u00e9e pour ce dossier."
                      : "S\u00e9lectionnez un dossier pour voir les mouvements."}
                  </td>
                </tr>
              ) : (
                entries.map((e) => (
                  <tr key={e.id} className="hover:bg-neutral-50 transition-colors">
                    <td className="px-6 py-4 text-sm text-neutral-900">{e.entry_date}</td>
                    <td className="px-6 py-4 text-sm font-medium">
                      <span className={TYPE_COLORS[e.entry_type] || "text-neutral-700"}>
                        {TYPE_LABELS[e.entry_type] || e.entry_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-neutral-500">{e.reference}</td>
                    <td className={`px-6 py-4 text-sm font-medium text-right ${TYPE_COLORS[e.entry_type] || "text-neutral-900"}`}>
                      {e.entry_type === "withdrawal" ? "-" : "+"}{formatCents(e.amount_cents)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
