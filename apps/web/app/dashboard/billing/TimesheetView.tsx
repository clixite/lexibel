"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState, useRef } from "react";
import { Plus, Play, Square, Loader2, X, Check } from "lucide-react";
import { apiFetch } from "@/lib/api";
import SkeletonTable from "@/components/skeletons/SkeletonTable";

interface TimeEntry {
  id: string;
  date: string;
  description: string;
  duration_minutes: number;
  rounding_rule: string;
  status: string;
  case_id: string;
  source: string;
  billable: boolean;
  hourly_rate_cents: number | null;
}

interface CaseOption {
  id: string;
  reference: string;
  title: string;
}

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-700",
  submitted: "bg-accent-50 text-accent-700",
  approved: "bg-success-50 text-success-700",
  invoiced: "bg-purple-100 text-purple-700",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Brouillon",
  submitted: "Soumis",
  approved: "Approuvé",
  invoiced: "Facturé",
};

export default function TimesheetView() {
  const { data: session } = useSession();
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [cases, setCases] = useState<CaseOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
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
    billable: true,
    hourly_rate_cents: 15000,
  });

  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;

  useEffect(() => {
    if (!token) return;
    Promise.all([
      apiFetch<{ items: TimeEntry[] }>("/time-entries", token, { tenantId }),
      apiFetch<{ items: CaseOption[] }>("/cases", token, { tenantId }),
    ])
      .then(([timeData, caseData]) => {
        setEntries(timeData.items);
        setCases(caseData.items);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token, tenantId]);

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
    setFormData((f) => ({ ...f, duration_minutes: minutes, source: "TIMER" }));
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
    setError(null);
    try {
      await apiFetch("/time-entries", token, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          case_id: formData.case_id,
          description: formData.description,
          date: formData.date,
          duration_minutes: formData.duration_minutes,
          rounding_rule: formData.rounding_rule,
          billable: formData.billable,
          hourly_rate_cents: formData.hourly_rate_cents,
        }),
      });
      setShowForm(false);
      setFormData({
        case_id: "",
        description: "",
        date: new Date().toISOString().split("T")[0],
        duration_minutes: 0,
        rounding_rule: "6min",
        billable: true,
        hourly_rate_cents: 15000,
      });
      setSuccess("Prestation enregistrée");
      setTimeout(() => setSuccess(null), 3000);
      // Reload
      const data = await apiFetch<{ items: TimeEntry[] }>("/time-entries", token, { tenantId });
      setEntries(data.items);
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (loading) {
    return <SkeletonTable />;
  }

  return (
    <div>
      {/* Success toast */}
      {success && (
        <div className="fixed top-4 right-4 z-50 bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-md text-sm flex items-center gap-2 shadow-lg">
          <Check className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* Actions bar */}
      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={() => {
            setFormData((f) => ({ ...f, duration_minutes: 0 }));
            setShowForm(true);
          }}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nouvelle prestation
        </button>

        {/* Timer */}
        {timerRunning ? (
          <button
            onClick={stopTimer}
            className="flex items-center gap-2 px-4 py-2 bg-danger text-white rounded-md text-sm font-medium hover:bg-danger/90 transition-colors"
          >
            <Square className="w-4 h-4" />
            {formatTimer(timerSeconds)} — Arrêter
          </button>
        ) : (
          <button
            onClick={startTimer}
            className="flex items-center gap-2 px-4 py-2 bg-success text-white rounded-md text-sm font-medium hover:bg-success/90 transition-colors"
          >
            <Play className="w-4 h-4" />
            Timer
          </button>
        )}
      </div>

      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Form */}
      {showForm && (
        <div className="card mb-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-neutral-900">
              Nouvelle prestation
            </h3>
            <button
              onClick={() => setShowForm(false)}
              className="text-neutral-400 hover:text-neutral-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Dossier
              </label>
              <select
                value={formData.case_id}
                onChange={(e) =>
                  setFormData((f) => ({ ...f, case_id: e.target.value }))
                }
                className="input"
              >
                <option value="">Sélectionner un dossier...</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.reference} — {c.title}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Date
              </label>
              <input
                type="date"
                value={formData.date}
                onChange={(e) =>
                  setFormData((f) => ({ ...f, date: e.target.value }))
                }
                className="input"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData((f) => ({ ...f, description: e.target.value }))
                }
                placeholder="Décrivez la prestation effectuée..."
                className="input"
                rows={2}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Durée (minutes)
              </label>
              <input
                type="number"
                min={1}
                value={formData.duration_minutes}
                onChange={(e) =>
                  setFormData((f) => ({
                    ...f,
                    duration_minutes: parseInt(e.target.value) || 0,
                  }))
                }
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Taux horaire (EUR)
              </label>
              <input
                type="number"
                min={0}
                step={0.01}
                value={(formData.hourly_rate_cents / 100).toFixed(2)}
                onChange={(e) =>
                  setFormData((f) => ({
                    ...f,
                    hourly_rate_cents: Math.round(
                      parseFloat(e.target.value || "0") * 100
                    ),
                  }))
                }
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Arrondi
              </label>
              <select
                value={formData.rounding_rule}
                onChange={(e) =>
                  setFormData((f) => ({ ...f, rounding_rule: e.target.value }))
                }
                className="input"
              >
                <option value="6min">6 minutes</option>
                <option value="10min">10 minutes</option>
                <option value="15min">15 minutes</option>
                <option value="none">Pas d&apos;arrondi</option>
              </select>
            </div>
            <div className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                id="billable"
                checked={formData.billable}
                onChange={(e) =>
                  setFormData((f) => ({ ...f, billable: e.target.checked }))
                }
                className="w-4 h-4 text-accent rounded border-neutral-300"
              />
              <label
                htmlFor="billable"
                className="text-sm font-medium text-neutral-700"
              >
                Facturable
              </label>
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <button
              onClick={handleSubmitEntry}
              disabled={!formData.case_id || !formData.description}
              className="btn-primary disabled:opacity-50"
            >
              Enregistrer
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-neutral-200">
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Date
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Dossier
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Description
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Durée
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Montant
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Statut
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {entries.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="px-6 py-12 text-center text-sm text-neutral-400"
                >
                  Aucune prestation trouvée.
                </td>
              </tr>
            ) : (
              entries.map((e) => {
                const caseRef =
                  cases.find((c) => c.id === e.case_id)?.reference || "—";
                const amount =
                  e.hourly_rate_cents && e.duration_minutes
                    ? (
                        (e.hourly_rate_cents / 100) *
                        (e.duration_minutes / 60)
                      ).toFixed(2) + " €"
                    : "—";
                return (
                  <tr
                    key={e.id}
                    className="hover:bg-neutral-50 transition-colors"
                  >
                    <td className="px-6 py-4 text-sm text-neutral-900">
                      {new Date(e.date).toLocaleDateString("fr-BE")}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-accent">
                      {caseRef}
                    </td>
                    <td className="px-6 py-4 text-sm text-neutral-700 max-w-xs truncate">
                      {e.description}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-neutral-900">
                      {formatDuration(e.duration_minutes)}
                    </td>
                    <td className="px-6 py-4 text-sm text-neutral-900">
                      {amount}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          STATUS_COLORS[e.status] ||
                          "bg-neutral-100 text-neutral-700"
                        }`}
                      >
                        {STATUS_LABELS[e.status] || e.status}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
