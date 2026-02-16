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

function formatCents(cents: number): string {
  return (cents / 100).toFixed(2) + " €";
}

const TYPE_COLORS: Record<string, string> = {
  deposit: "text-green-600",
  withdrawal: "text-red-600",
  interest: "text-blue-600",
};

const TYPE_LABELS: Record<string, string> = {
  deposit: "Dépôt",
  withdrawal: "Retrait",
  interest: "Intérêts",
};

export default function ThirdPartyView() {
  const { data: session } = useSession();
  const [balance, setBalance] = useState<Balance | null>(null);
  const [entries, setEntries] = useState<ThirdPartyEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    case_id: "",
    entry_type: "deposit",
    amount_cents: 0,
    reference: "",
    entry_date: new Date().toISOString().split("T")[0],
  });

  const token = (session?.user as any)?.accessToken;

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    // We need a case_id to fetch — for now show empty state
    setLoading(false);
  }, [token]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div>
      {/* Balance card */}
      {balance && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Dépôts</p>
            <p className="text-xl font-bold text-green-600">{formatCents(balance.deposits)}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Retraits</p>
            <p className="text-xl font-bold text-red-600">{formatCents(balance.withdrawals)}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Intérêts</p>
            <p className="text-xl font-bold text-blue-600">{formatCents(balance.interest)}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Solde</p>
            <p className="text-xl font-bold text-gray-900">{formatCents(balance.balance)}</p>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">
          Sélectionnez un dossier pour voir les mouvements du compte de tiers.
        </p>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nouvelle écriture
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>
      )}

      {/* Form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Nouvelle écriture</h3>
            <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600">
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Dossier (Case ID)</label>
              <input
                type="text"
                placeholder="UUID du dossier"
                value={formData.case_id}
                onChange={(e) => setFormData((f) => ({ ...f, case_id: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select
                value={formData.entry_type}
                onChange={(e) => setFormData((f) => ({ ...f, entry_type: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="deposit">Dépôt</option>
                <option value="withdrawal">Retrait</option>
                <option value="interest">Intérêts</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Montant (€)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={(formData.amount_cents / 100).toFixed(2)}
                onChange={(e) => setFormData((f) => ({ ...f, amount_cents: Math.round(parseFloat(e.target.value) * 100) || 0 }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Référence</label>
              <input
                type="text"
                value={formData.reference}
                onChange={(e) => setFormData((f) => ({ ...f, reference: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors">
              Enregistrer
            </button>
          </div>
        </div>
      )}

      {/* Entries table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Référence</th>
              <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Montant</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {entries.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-8 text-center text-sm text-gray-400">
                  Aucune écriture trouvée. Sélectionnez un dossier pour voir les mouvements.
                </td>
              </tr>
            ) : (
              entries.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-sm text-gray-900">{e.entry_date}</td>
                  <td className="px-6 py-4 text-sm font-medium">
                    <span className={TYPE_COLORS[e.entry_type] || "text-gray-700"}>
                      {TYPE_LABELS[e.entry_type] || e.entry_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">{e.reference}</td>
                  <td className={`px-6 py-4 text-sm font-medium text-right ${TYPE_COLORS[e.entry_type] || "text-gray-900"}`}>
                    {e.entry_type === "withdrawal" ? "-" : "+"}{formatCents(e.amount_cents)}
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
