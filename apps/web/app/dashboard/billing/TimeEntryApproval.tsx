"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { Check, X, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface TimeEntry {
  id: string;
  date: string;
  description: string;
  duration_minutes: number;
  rounding_rule: string;
  status: string;
  case_id: string;
  user_id: string;
}

export default function TimeEntryApproval() {
  const { data: session } = useSession();
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [processing, setProcessing] = useState(false);

  const token = (session?.user as any)?.accessToken;

  useEffect(() => {
    if (!token) return;
    apiFetch<{ items: TimeEntry[] }>("/time-entries?status=submitted", token)
      .then((data) => setEntries(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === entries.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(entries.map((e) => e.id)));
    }
  };

  const batchAction = async (action: "approve" | "reject") => {
    if (!token || selected.size === 0) return;
    setProcessing(true);
    try {
      const endpoint = action === "approve" ? "approve" : "refuse";
      Array.from(selected).forEach(async (id) => {
        await apiFetch(`/time-entries/${id}/${endpoint}`, token, { method: "POST" });
      });
      // Reload
      const data = await apiFetch<{ items: TimeEntry[] }>("/time-entries?status=submitted", token);
      setEntries(data.items);
      setSelected(new Set());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setProcessing(false);
    }
  };

  const formatDuration = (minutes: number) => {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return h > 0 ? `${h}h${m.toString().padStart(2, "0")}` : `${m}min`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="mt-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Approbation des prestations
      </h3>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>
      )}

      {entries.length > 0 && (
        <div className="flex items-center gap-3 mb-4">
          <span className="text-sm text-gray-500">
            {selected.size} / {entries.length} sélectionnée(s)
          </span>
          <button
            onClick={() => batchAction("approve")}
            disabled={selected.size === 0 || processing}
            className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-50"
          >
            <Check className="w-4 h-4" />
            Approuver
          </button>
          <button
            onClick={() => batchAction("reject")}
            disabled={selected.size === 0 || processing}
            className="flex items-center gap-1 px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors disabled:opacity-50"
          >
            <X className="w-4 h-4" />
            Refuser
          </button>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="w-10 px-4 py-3">
                <input
                  type="checkbox"
                  checked={entries.length > 0 && selected.size === entries.length}
                  onChange={selectAll}
                  className="rounded border-gray-300"
                />
              </th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Durée</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Arrondi</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {entries.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-sm text-gray-400">
                  Aucune prestation en attente d&apos;approbation.
                </td>
              </tr>
            ) : (
              entries.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-4">
                    <input
                      type="checkbox"
                      checked={selected.has(e.id)}
                      onChange={() => toggleSelect(e.id)}
                      className="rounded border-gray-300"
                    />
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">{e.date}</td>
                  <td className="px-6 py-4 text-sm text-gray-700 max-w-xs truncate">{e.description}</td>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{formatDuration(e.duration_minutes)}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{e.rounding_rule}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
