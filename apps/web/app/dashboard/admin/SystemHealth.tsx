"use client";

import { useState, useEffect } from "react";
import { Activity, RefreshCw, Loader2 } from "lucide-react";

interface ServiceStatus {
  status: string;
  version?: string;
}

interface HealthData {
  status: string;
  services: Record<string, ServiceStatus>;
  checked_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  healthy: "bg-green-500",
  degraded: "bg-amber-500",
  unhealthy: "bg-red-500",
  unavailable: "bg-red-500",
  not_configured: "bg-slate-400",
};

const STATUS_LABELS: Record<string, string> = {
  healthy: "En ligne",
  degraded: "Dégradé",
  unhealthy: "Erreur",
  unavailable: "Indisponible",
  not_configured: "Non configuré",
};

export default function SystemHealth() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<Record<string, number> | null>(null);

  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const [healthRes, statsRes] = await Promise.all([
        fetch(`${apiUrl}/admin/health`, { credentials: "include" }),
        fetch(`${apiUrl}/admin/stats`, { credentials: "include" }),
      ]);
      if (healthRes.ok) setHealth(await healthRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Activity className="w-5 h-5 text-indigo-500" />
          Santé du système
        </h2>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50 flex items-center gap-1"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Rafraîchir
        </button>
      </div>

      {/* Global Status */}
      {health && (
        <div
          className={`p-4 rounded-xl text-white ${
            health.status === "healthy" ? "bg-green-600" : "bg-amber-600"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-lg font-semibold">
              {health.status === "healthy"
                ? "Tous les services sont opérationnels"
                : "Certains services sont dégradés"}
            </span>
            <span className="text-sm opacity-80">
              {health.checked_at?.slice(0, 19).replace("T", " ")}
            </span>
          </div>
        </div>
      )}

      {/* Service Grid */}
      {health && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(health.services).map(([name, svc]) => (
            <div
              key={name}
              className="bg-white border border-slate-200 rounded-xl p-4"
            >
              <div className="flex items-center gap-2 mb-2">
                <div
                  className={`w-2.5 h-2.5 rounded-full ${STATUS_COLORS[svc.status] || "bg-slate-400"}`}
                />
                <span className="text-sm font-semibold capitalize">{name}</span>
              </div>
              <span
                className={`text-xs ${
                  svc.status === "healthy" ? "text-green-600" : "text-slate-500"
                }`}
              >
                {STATUS_LABELS[svc.status] || svc.status}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h3 className="text-md font-semibold mb-4">Statistiques globales</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
            {[
              { label: "Tenants", value: stats.tenants },
              { label: "Utilisateurs", value: stats.users },
              { label: "Dossiers", value: stats.cases },
              { label: "Documents", value: stats.documents },
              { label: "Factures", value: stats.invoices },
            ].map((s) => (
              <div key={s.label} className="p-3 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold text-slate-900">
                  {s.value ?? 0}
                </div>
                <div className="text-xs text-slate-500">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
