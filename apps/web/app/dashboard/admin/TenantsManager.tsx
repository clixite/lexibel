"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Building2, Loader2, Plus, Check } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface Tenant {
  id: string;
  name: string;
  slug: string;
  plan: string;
  locale: string;
  status: string;
  created_at: string | null;
}

const PLANS = [
  { value: "solo", label: "Solo" },
  { value: "team", label: "Team" },
  { value: "enterprise", label: "Enterprise" },
];

export default function TenantsManager() {
  const { data: session } = useSession();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [plan, setPlan] = useState("solo");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;

  const fetchTenants = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await apiFetch<{ tenants: Tenant[] }>("/admin/tenants", token, { tenantId });
      setTenants(data.tenants || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTenants();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const createTenant = async () => {
    if (!name.trim() || !token) return;
    setCreating(true);
    setError("");

    try {
      await apiFetch("/admin/tenants", token, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          name,
          slug: slug || name.toLowerCase().replace(/\s+/g, "-"),
          plan,
        }),
      });
      setName("");
      setSlug("");
      setPlan("solo");
      setShowForm(false);
      setSuccess("Tenant créé avec succès");
      fetchTenants();
      setTimeout(() => setSuccess(""), 3000);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Success toast */}
      {success && (
        <div className="bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-md text-sm flex items-center gap-2">
          <Check className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-neutral-900 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-accent" />
          Tenants
        </h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nouveau tenant
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="card">
          <h3 className="text-base font-semibold text-neutral-900 mb-4">
            Créer un tenant
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Nom
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Cabinet Dupont"
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Slug
              </label>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="cabinet-dupont"
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Plan
              </label>
              <select
                value={plan}
                onChange={(e) => setPlan(e.target.value)}
                className="input"
              >
                {PLANS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {error && <p className="mt-2 text-sm text-danger">{error}</p>}
          <div className="mt-4 flex gap-2">
            <button
              onClick={createTenant}
              disabled={creating || !name.trim()}
              className="btn-primary flex items-center gap-2 disabled:opacity-50"
            >
              {creating && <Loader2 className="w-4 h-4 animate-spin" />}
              Créer
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-4 py-2 text-sm font-medium text-neutral-600 bg-neutral-100 rounded-md hover:bg-neutral-200 transition-colors"
            >
              Annuler
            </button>
          </div>
        </div>
      )}

      {/* Tenants List */}
      <div className="card">
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
          </div>
        ) : tenants.length === 0 ? (
          <p className="text-sm text-neutral-500 py-4">Aucun tenant.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Nom
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Slug
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Plan
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Statut
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Créé le
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {tenants.map((t) => (
                  <tr key={t.id} className="hover:bg-neutral-50 transition-colors">
                    <td className="py-3 px-4 font-medium text-neutral-900">
                      {t.name}
                    </td>
                    <td className="py-3 px-4 text-neutral-500">{t.slug}</td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-accent-50 text-accent-700">
                        {t.plan}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-success-50 text-success-700">
                        {t.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-neutral-500 text-xs">
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
