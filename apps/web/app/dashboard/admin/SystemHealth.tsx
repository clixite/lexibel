"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Activity, RefreshCw, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface ServiceStatus {
  status: string;
  version?: string;
}

interface HealthData {
  status: string;
  services: Record<string, ServiceStatus>;
  checked_at: string;
}

interface StatsData {
  tenants: number;
  users: number;
  cases: number;
  contacts: number;
  invoices: number;
  checked_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  healthy: "bg-success",
  degraded: "bg-warning",
  unhealthy: "bg-danger",
  unavailable: "bg-danger",
  not_configured: "bg-neutral-400",
};

const STATUS_LABELS: Record<string, string> = {
  healthy: "En ligne",
  degraded: "Dégradé",
  unhealthy: "Erreur",
  unavailable: "Indisponible",
  not_configured: "Non configuré",
};

export default function SystemHealth() {
  const { data: session } = useSession();
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;

  const fetchHealth = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [healthData, statsData] = await Promise.all([
        apiFetch<HealthData>("/admin/health", token, { tenantId }),
        apiFetch<StatsData>("/admin/stats", token, { tenantId }),
      ]);
      setHealth(healthData);
      setStats(statsData);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-neutral-900 flex items-center gap-2">
          <Activity className="w-5 h-5 text-accent" />
          Santé du système
        </h2>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="px-3 py-1.5 text-sm font-medium text-neutral-600 bg-neutral-100 rounded-md hover:bg-neutral-200 transition-colors flex items-center gap-1.5 disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Rafraîchir
        </button>
      </div>

      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md text-sm">
          {error}
        </div>
      )}

      {/* Global Status */}
      {health && (
        <div
          className={`p-4 rounded-lg text-white ${
            health.status === "healthy" ? "bg-success" : "bg-warning"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-base font-semibold">
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
            <div key={name} className="card">
              <div className="flex items-center gap-2 mb-2">
                <div
                  className={`w-2.5 h-2.5 rounded-full ${STATUS_COLORS[svc.status] || "bg-neutral-400"}`}
                />
                <span className="text-sm font-semibold text-neutral-900 capitalize">
                  {name}
                </span>
              </div>
              <span
                className={`text-xs ${
                  svc.status === "healthy" ? "text-success" : "text-neutral-500"
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
        <div className="card">
          <h3 className="text-base font-semibold text-neutral-900 mb-4">
            Statistiques globales
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
            {[
              { label: "Tenants", value: stats.tenants },
              { label: "Utilisateurs", value: stats.users },
              { label: "Dossiers", value: stats.cases },
              { label: "Contacts", value: stats.contacts },
              { label: "Factures", value: stats.invoices },
            ].map((s) => (
              <div key={s.label} className="p-3 bg-neutral-50 rounded-md">
                <div className="text-2xl font-bold text-neutral-900">
                  {s.value ?? 0}
                </div>
                <div className="text-xs text-neutral-500">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
