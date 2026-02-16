"use client";

import { useState, useEffect } from "react";
import { Building2, Loader2, Plus } from "lucide-react";

interface Tenant {
  id: string;
  name: string;
  domain: string;
  plan: string;
  status: string;
  created_at: string;
}

const PLANS = [
  { value: "standard", label: "Standard" },
  { value: "professional", label: "Professional" },
  { value: "enterprise", label: "Enterprise" },
];

export default function TenantsManager() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [plan, setPlan] = useState("standard");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  const fetchTenants = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/admin/tenants`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setTenants(data.tenants || []);
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTenants();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const createTenant = async () => {
    if (!name.trim()) return;
    setCreating(true);
    setError("");

    try {
      const res = await fetch(`${apiUrl}/admin/tenants`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ name, domain, plan }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `Erreur ${res.status}`);
      }
      setName("");
      setDomain("");
      setPlan("standard");
      setShowForm(false);
      fetchTenants();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erreur inconnue");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Building2 className="w-5 h-5 text-indigo-500" />
          Tenants
        </h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 flex items-center gap-1"
        >
          <Plus className="w-4 h-4" />
          Nouveau
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h3 className="text-md font-semibold mb-4">Créer un tenant</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Nom
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Cabinet Dupont"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Domaine
              </label>
              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="dupont.lexibel.be"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Plan
              </label>
              <select
                value={plan}
                onChange={(e) => setPlan(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {PLANS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
          <div className="mt-4 flex gap-2">
            <button
              onClick={createTenant}
              disabled={creating || !name.trim()}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
            >
              {creating && <Loader2 className="w-4 h-4 animate-spin" />}
              Créer
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50"
            >
              Annuler
            </button>
          </div>
        </div>
      )}

      {/* Tenants List */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
          </div>
        ) : tenants.length === 0 ? (
          <p className="text-sm text-slate-500 py-4">Aucun tenant.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-3 font-medium text-slate-600">
                    Nom
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-slate-600">
                    Domaine
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-slate-600">
                    Plan
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-slate-600">
                    Statut
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-slate-600">
                    Créé le
                  </th>
                </tr>
              </thead>
              <tbody>
                {tenants.map((t) => (
                  <tr key={t.id} className="border-b border-slate-100">
                    <td className="py-2 px-3 font-medium">{t.name}</td>
                    <td className="py-2 px-3 text-slate-500">{t.domain || "—"}</td>
                    <td className="py-2 px-3">
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-indigo-50 text-indigo-600">
                        {t.plan}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-600">
                        {t.status}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-500 text-xs">
                      {t.created_at?.slice(0, 10)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
