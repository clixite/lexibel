"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState, useRef } from "react";
import { Plus, Play, Square, Loader2, X } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface TimeEntry {
  id: string;
  date: string;
  description: string;
  duration_minutes: number;
  rounding_rule: string;
  status: string;
  case_id: string;
  source: string;
}

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  submitted: "bg-blue-100 text-blue-700",
  approved: "bg-green-100 text-green-700",
  invoiced: "bg-purple-100 text-purple-700",
};

export default function TimesheetView() {
  const { data: session } = useSession();
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  // Timer state
  const [timerRunning, setTimerRunning] = useState(false);
  const [timerSeconds, setTimerSeconds] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    case_id: "",
    description: "",
    date: new Date().toISOString().split("T")[0],
    duration_minutes: 0,
    rounding_rule: "6min",
  });

  const token = (session?.user as any)?.accessToken;

  useEffect(() => {
    if (!token) return;
    apiFetch<{ items: TimeEntry[] }>("/time-entries", token)
      .then((data) => setEntries(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  // Timer effect
  useEffect(() => {
    if (timerRunning) {
      timerRef.current = setInterval(() => {
        setTimerSeconds((s) => s + 1);
      }, 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [timerRunning]);

  const startTimer = () => {
    setTimerSeconds(0);
    setTimerRunning(true);
  };

  const stopTimer = () => {
    setTimerRunning(false);
    const minutes = Math.ceil(timerSeconds / 60);
    setFormData((f) => ({ ...f, duration_minutes: minutes }));
    setShowForm(true);
  };

  const formatTimer = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const formatDuration = (minutes: number) => {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return h > 0 ? `${h}h${m.toString().padStart(2, "0")}` : `${m}min`;
  };

  const handleSubmitEntry = async () => {
    if (!token || !formData.case_id || !formData.description) return;
    try {
      await apiFetch("/time-entries", token, {
        method: "POST",
        body: JSON.stringify({
          case_id: formData.case_id,
          description: formData.description,
          date: formData.date,
          duration_minutes: formData.duration_minutes,
          rounding_rule: formData.rounding_rule,
          user_id: (session?.user as any)?.id || "00000000-0000-4000-a000-000000000010",
        }),
      });
      setShowForm(false);
      setFormData({ case_id: "", description: "", date: new Date().toISOString().split("T")[0], duration_minutes: 0, rounding_rule: "6min" });
      // Reload
      const data = await apiFetch<{ items: TimeEntry[] }>("/time-entries", token);
      setEntries(data.items);
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div>
      {/* Actions bar */}
      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={() => { setFormData((f) => ({ ...f, duration_minutes: 0 })); setShowForm(true); }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Nouvelle prestation
        </button>

        {/* Timer */}
        {timerRunning ? (
          <button
            onClick={stopTimer}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
          >
            <Square className="w-4 h-4" />
            {formatTimer(timerSeconds)} — Arrêter
          </button>
        ) : (
          <button
            onClick={startTimer}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
          >
            <Play className="w-4 h-4" />
            Timer
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">{error}</div>
      )}

      {/* Form modal */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Nouvelle prestation</h3>
            <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600">
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Case ID</label>
              <input
                type="text"
                placeholder="UUID du dossier"
                value={formData.case_id}
                onChange={(e) => setFormData((f) => ({ ...f, case_id: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
              <input
                type="date"
                value={formData.date}
                onChange={(e) => setFormData((f) => ({ ...f, date: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData((f) => ({ ...f, description: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                rows={2}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Durée (minutes)</label>
              <input
                type="number"
                min={1}
                value={formData.duration_minutes}
                onChange={(e) => setFormData((f) => ({ ...f, duration_minutes: parseInt(e.target.value) || 0 }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Arrondi</label>
              <select
                value={formData.rounding_rule}
                onChange={(e) => setFormData((f) => ({ ...f, rounding_rule: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="6min">6 minutes</option>
                <option value="10min">10 minutes</option>
                <option value="15min">15 minutes</option>
                <option value="none">Pas d&apos;arrondi</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <button
              onClick={handleSubmitEntry}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              Enregistrer
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Durée</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Arrondi</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {entries.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-sm text-gray-400">
                  Aucune prestation trouvée.
                </td>
              </tr>
            ) : (
              entries.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-sm text-gray-900">{e.date}</td>
                  <td className="px-6 py-4 text-sm text-gray-700 max-w-xs truncate">{e.description}</td>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{formatDuration(e.duration_minutes)}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{e.rounding_rule}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{e.source}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[e.status] || "bg-gray-100 text-gray-700"}`}>
                      {e.status}
                    </span>
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
