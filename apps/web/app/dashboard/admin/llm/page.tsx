"use client";

import { useAuth } from "@/lib/useAuth";
import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Brain,
  Server,
  FileSearch,
  BarChart3,
  Shield,
  Settings,
  RefreshCw,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Download,
  ChevronLeft,
  ChevronRight,
  Eye,
  EyeOff,
  Power,
  PowerOff,
  Search,
  Filter,
  TrendingUp,
  DollarSign,
  Clock,
  FileText,
  Key,
} from "lucide-react";
import { apiFetch } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ProviderInfo {
  name: string;
  tier: number;
  status: string;
  default_model: string;
  cost_per_1k_input: number;
  cost_per_1k_output: number;
  supports_streaming: boolean;
  enabled: boolean;
}

interface ProvidersResponse {
  providers: Record<string, ProviderInfo>;
}

interface AuditItem {
  id: string;
  created_at: string;
  provider: string;
  model: string;
  data_sensitivity: string;
  was_anonymized: boolean;
  purpose: string;
  token_count_input: number | null;
  token_count_output: number | null;
  cost_estimate_eur: number | null;
  latency_ms: number | null;
  human_validated: boolean;
  error: string | null;
}

interface AuditResponse {
  items: AuditItem[];
  total: number;
  page: number;
  per_page: number;
}

interface ProviderStat {
  provider: string;
  count: number;
  cost_eur: number;
  tokens_in: number;
  tokens_out: number;
  avg_latency_ms: number;
}

interface StatsResponse {
  period_days: number;
  total_requests: number;
  total_cost_eur: number;
  human_validated_count: number;
  human_validation_rate: number;
  by_provider: ProviderStat[];
  by_sensitivity: Record<string, number>;
}

interface DPIAReport {
  report_type: string;
  regulation: string;
  generated_at: string;
  system_classification: string;
  processing_description: {
    purpose: string;
    legal_basis: string;
    data_categories: string[];
    data_subjects: string;
    retention_period: string;
  };
  sub_processors: Record<string, any>;
  safeguards: Record<string, string>;
  statistics: {
    total_requests: number;
    anonymized_requests: number;
    anonymization_rate: number;
    error_count: number;
    error_rate: number;
    usage_by_provider: any[];
    usage_by_sensitivity: Record<string, number>;
    human_validation_rate: number;
    total_cost_eur: number;
  };
  risk_assessment: {
    identified_risks: string[];
    mitigation_measures: string[];
    residual_risk: string;
  };
}

interface ClassifyResponse {
  sensitivity: string;
  allowed_providers: string[];
  detected_entities: string[];
  reasons: string[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TABS = [
  { id: "providers", label: "Providers", icon: Server, description: "Statut et gestion des fournisseurs LLM" },
  { id: "audit", label: "Audit", icon: FileSearch, description: "Journaux d'audit des requetes LLM" },
  { id: "stats", label: "Statistiques", icon: BarChart3, description: "Utilisation, couts et tendances" },
  { id: "dpia", label: "DPIA", icon: Shield, description: "Rapport d'analyse d'impact (RGPD)" },
  { id: "config", label: "Configuration", icon: Settings, description: "Cles API et parametres" },
] as const;

type TabId = (typeof TABS)[number]["id"];

const SENSITIVITY_COLORS: Record<string, string> = {
  public: "bg-green-100 text-green-800 border-green-200",
  semi: "bg-yellow-100 text-yellow-800 border-yellow-200",
  sensitive: "bg-orange-100 text-orange-800 border-orange-200",
  critical: "bg-red-100 text-red-800 border-red-200",
};

const SENSITIVITY_DOT_COLORS: Record<string, string> = {
  public: "bg-green-500",
  semi: "bg-yellow-500",
  sensitive: "bg-orange-500",
  critical: "bg-red-500",
};

const SENSITIVITY_LABELS: Record<string, string> = {
  public: "Public",
  semi: "Semi-sensible",
  sensitive: "Sensible",
  critical: "Critique",
};

const TIER_COLORS: Record<number, string> = {
  1: "bg-green-100 text-green-800",
  2: "bg-yellow-100 text-yellow-800",
  3: "bg-orange-100 text-orange-800",
};

const TIER_LABELS: Record<number, string> = {
  1: "Tier 1 - EU-Safe",
  2: "Tier 2 - Anonymise",
  3: "Tier 3 - Public Only",
};

const STATUS_DOT: Record<string, string> = {
  healthy: "bg-green-500",
  unhealthy: "bg-red-500",
  disabled: "bg-neutral-400",
};

// ---------------------------------------------------------------------------
// Helper components
// ---------------------------------------------------------------------------

function StatusDot({ status, enabled }: { status: string; enabled: boolean }) {
  const color = !enabled ? "bg-neutral-400" : (STATUS_DOT[status] || "bg-neutral-400");
  return (
    <span className="relative flex h-3 w-3">
      {enabled && status === "healthy" && (
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
      )}
      <span className={`relative inline-flex rounded-full h-3 w-3 ${color}`} />
    </span>
  );
}

function SensitivityBadge({ sensitivity }: { sensitivity: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${
        SENSITIVITY_COLORS[sensitivity] || "bg-neutral-100 text-neutral-700 border-neutral-200"
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${SENSITIVITY_DOT_COLORS[sensitivity] || "bg-neutral-400"}`} />
      {SENSITIVITY_LABELS[sensitivity] || sensitivity}
    </span>
  );
}

function TierBadge({ tier }: { tier: number }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
        TIER_COLORS[tier] || "bg-neutral-100 text-neutral-700"
      }`}
    >
      {TIER_LABELS[tier] || `Tier ${tier}`}
    </span>
  );
}

function LoadingSpinner({ message }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3">
      <Loader2 className="w-8 h-8 animate-spin text-accent" />
      {message && <p className="text-sm text-neutral-500">{message}</p>}
    </div>
  );
}

function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-lg text-sm flex items-center gap-3">
      <AlertCircle className="w-5 h-5 flex-shrink-0" />
      <span className="flex-1">{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1 text-xs font-medium bg-danger-100 hover:bg-danger-200 rounded transition-colors"
        >
          Reessayer
        </button>
      )}
    </div>
  );
}

function EmptyState({ icon: Icon, title, description }: { icon: any; title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="w-12 h-12 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
        <Icon className="w-6 h-6 text-neutral-400" />
      </div>
      <h3 className="text-sm font-semibold text-neutral-700 mb-1">{title}</h3>
      <p className="text-xs text-neutral-500 max-w-sm">{description}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Providers
// ---------------------------------------------------------------------------

function ProvidersTab({ token, tenantId }: { token: string; tenantId?: string }) {
  const [providers, setProviders] = useState<Record<string, ProviderInfo>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingProvider, setTogglingProvider] = useState<string | null>(null);

  // Classify tester
  const [classifyText, setClassifyText] = useState("");
  const [classifyResult, setClassifyResult] = useState<ClassifyResponse | null>(null);
  const [classifyLoading, setClassifyLoading] = useState(false);

  const fetchProviders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ProvidersResponse>("/llm/providers", token, { tenantId });
      setProviders(data.providers || {});
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token, tenantId]);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  const handleToggle = async (providerName: string, currentEnabled: boolean) => {
    setTogglingProvider(providerName);
    try {
      await apiFetch(`/llm/providers/${providerName}`, token, {
        method: "PATCH",
        tenantId,
        body: JSON.stringify({ enabled: !currentEnabled }),
      });
      setProviders((prev) => ({
        ...prev,
        [providerName]: { ...prev[providerName], enabled: !currentEnabled },
      }));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setTogglingProvider(null);
    }
  };

  const handleClassify = async () => {
    if (!classifyText.trim()) return;
    setClassifyLoading(true);
    setClassifyResult(null);
    try {
      const result = await apiFetch<ClassifyResponse>("/llm/classify", token, {
        method: "POST",
        tenantId,
        body: JSON.stringify({ text: classifyText }),
      });
      setClassifyResult(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setClassifyLoading(false);
    }
  };

  if (loading) return <LoadingSpinner message="Chargement des providers..." />;

  const providerList = Object.values(providers);
  const healthyCount = providerList.filter((p) => p.enabled && p.status === "healthy").length;
  const totalCount = providerList.length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-neutral-900 flex items-center gap-2">
            <Server className="w-5 h-5 text-accent" />
            Fournisseurs LLM
          </h2>
          <p className="text-xs text-neutral-500 mt-1">
            {healthyCount}/{totalCount} fournisseurs actifs
          </p>
        </div>
        <button
          onClick={fetchProviders}
          disabled={loading}
          className="px-3 py-1.5 text-sm font-medium text-neutral-600 bg-neutral-100 rounded-md hover:bg-neutral-200 transition-colors flex items-center gap-1.5 disabled:opacity-50"
        >
          <RefreshCw className="w-4 h-4" />
          Rafraichir
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={fetchProviders} />}

      {/* Provider Cards */}
      {providerList.length === 0 ? (
        <EmptyState
          icon={Server}
          title="Aucun provider configure"
          description="Configurez vos cles API pour activer les providers LLM."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {providerList.map((provider) => (
            <div
              key={provider.name}
              className={`card border-2 transition-all duration-200 ${
                provider.enabled
                  ? provider.status === "healthy"
                    ? "border-green-200 hover:border-green-300"
                    : "border-red-200 hover:border-red-300"
                  : "border-neutral-200 opacity-75"
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <StatusDot status={provider.status} enabled={provider.enabled} />
                  <h3 className="font-semibold text-neutral-900 capitalize">{provider.name}</h3>
                </div>
                <button
                  onClick={() => handleToggle(provider.name, provider.enabled)}
                  disabled={togglingProvider === provider.name}
                  className={`p-1.5 rounded-md transition-colors ${
                    provider.enabled
                      ? "text-green-600 bg-green-50 hover:bg-green-100"
                      : "text-neutral-400 bg-neutral-100 hover:bg-neutral-200"
                  }`}
                  title={provider.enabled ? "Desactiver" : "Activer"}
                >
                  {togglingProvider === provider.name ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : provider.enabled ? (
                    <Power className="w-4 h-4" />
                  ) : (
                    <PowerOff className="w-4 h-4" />
                  )}
                </button>
              </div>

              <div className="space-y-2.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <TierBadge tier={provider.tier} />
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      provider.enabled
                        ? provider.status === "healthy"
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                        : "bg-neutral-100 text-neutral-500"
                    }`}
                  >
                    {provider.enabled
                      ? provider.status === "healthy"
                        ? "En ligne"
                        : "Erreur"
                      : "Desactive"}
                  </span>
                </div>

                <div className="text-xs text-neutral-600 space-y-1">
                  <div className="flex justify-between">
                    <span className="text-neutral-500">Modele :</span>
                    <span className="font-mono text-neutral-700">{provider.default_model}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-500">Cout input :</span>
                    <span className="font-mono text-neutral-700">
                      {provider.cost_per_1k_input.toFixed(4)} EUR/1k
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-500">Cout output :</span>
                    <span className="font-mono text-neutral-700">
                      {provider.cost_per_1k_output.toFixed(4)} EUR/1k
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-500">Streaming :</span>
                    <span>
                      {provider.supports_streaming ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-500 inline" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5 text-neutral-400 inline" />
                      )}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Classify Tester */}
      <div className="card">
        <h3 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
          <Search className="w-4 h-4 text-accent" />
          Tester la classification de sensibilite
        </h3>
        <div className="flex gap-3">
          <textarea
            value={classifyText}
            onChange={(e) => setClassifyText(e.target.value)}
            placeholder="Saisissez un texte pour tester la classification..."
            rows={3}
            className="flex-1 px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:ring-2 focus:ring-accent focus:border-accent resize-none"
          />
          <button
            onClick={handleClassify}
            disabled={classifyLoading || !classifyText.trim()}
            className="btn-primary self-end px-4 py-2 flex items-center gap-2 disabled:opacity-50"
          >
            {classifyLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Classifier
          </button>
        </div>

        {classifyResult && (
          <div className="mt-4 p-4 bg-neutral-50 rounded-lg space-y-3">
            <div className="flex items-center gap-3">
              <span className="text-xs font-medium text-neutral-500 uppercase">Sensibilite :</span>
              <SensitivityBadge sensitivity={classifyResult.sensitivity} />
            </div>
            <div>
              <span className="text-xs font-medium text-neutral-500 uppercase block mb-1.5">
                Providers autorises :
              </span>
              <div className="flex flex-wrap gap-1.5">
                {classifyResult.allowed_providers.map((p) => (
                  <span key={p} className="px-2 py-0.5 bg-white border border-neutral-200 rounded text-xs font-medium text-neutral-700 capitalize">
                    {p}
                  </span>
                ))}
              </div>
            </div>
            {classifyResult.detected_entities.length > 0 && (
              <div>
                <span className="text-xs font-medium text-neutral-500 uppercase block mb-1.5">
                  Entites detectees :
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {classifyResult.detected_entities.map((e, i) => (
                    <span key={i} className="px-2 py-0.5 bg-orange-50 border border-orange-200 rounded text-xs font-medium text-orange-700">
                      {e}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {classifyResult.reasons.length > 0 && (
              <div>
                <span className="text-xs font-medium text-neutral-500 uppercase block mb-1.5">Raisons :</span>
                <ul className="list-disc list-inside text-xs text-neutral-600 space-y-0.5">
                  {classifyResult.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Audit
// ---------------------------------------------------------------------------

function AuditTab({ token, tenantId }: { token: string; tenantId?: string }) {
  const [items, setItems] = useState<AuditItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filterProvider, setFilterProvider] = useState("");
  const [filterSensitivity, setFilterSensitivity] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  // Expanded row
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const fetchAudit = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        per_page: String(perPage),
      });
      if (filterProvider) params.set("provider", filterProvider);
      if (filterSensitivity) params.set("sensitivity", filterSensitivity);
      if (filterDateFrom) params.set("date_from", filterDateFrom);
      if (filterDateTo) params.set("date_to", filterDateTo);

      const data = await apiFetch<AuditResponse>(`/llm/audit?${params.toString()}`, token, { tenantId });
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token, tenantId, page, perPage, filterProvider, filterSensitivity, filterDateFrom, filterDateTo]);

  useEffect(() => {
    fetchAudit();
  }, [fetchAudit]);

  const totalPages = Math.max(1, Math.ceil(total / perPage));

  const clearFilters = () => {
    setFilterProvider("");
    setFilterSensitivity("");
    setFilterDateFrom("");
    setFilterDateTo("");
    setPage(1);
  };

  const hasActiveFilters = filterProvider || filterSensitivity || filterDateFrom || filterDateTo;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-base font-semibold text-neutral-900 flex items-center gap-2">
          <FileSearch className="w-5 h-5 text-accent" />
          Journal d'audit LLM
          <span className="text-xs font-normal text-neutral-500 ml-1">({total} entrees)</span>
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors flex items-center gap-1.5 ${
              showFilters || hasActiveFilters
                ? "bg-accent text-white"
                : "text-neutral-600 bg-neutral-100 hover:bg-neutral-200"
            }`}
          >
            <Filter className="w-4 h-4" />
            Filtres
            {hasActiveFilters && (
              <span className="w-2 h-2 rounded-full bg-white" />
            )}
          </button>
          <button
            onClick={fetchAudit}
            disabled={loading}
            className="px-3 py-1.5 text-sm font-medium text-neutral-600 bg-neutral-100 rounded-md hover:bg-neutral-200 transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Rafraichir
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={fetchAudit} />}

      {/* Filters Panel */}
      {showFilters && (
        <div className="card bg-neutral-50 border border-neutral-200">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1.5">Provider</label>
              <input
                type="text"
                value={filterProvider}
                onChange={(e) => { setFilterProvider(e.target.value); setPage(1); }}
                placeholder="ex: mistral, openai..."
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:ring-2 focus:ring-accent focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1.5">Sensibilite</label>
              <select
                value={filterSensitivity}
                onChange={(e) => { setFilterSensitivity(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:ring-2 focus:ring-accent focus:border-accent bg-white"
              >
                <option value="">Toutes</option>
                <option value="public">Public</option>
                <option value="semi">Semi-sensible</option>
                <option value="sensitive">Sensible</option>
                <option value="critical">Critique</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1.5">Date debut</label>
              <input
                type="date"
                value={filterDateFrom}
                onChange={(e) => { setFilterDateFrom(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:ring-2 focus:ring-accent focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1.5">Date fin</label>
              <input
                type="date"
                value={filterDateTo}
                onChange={(e) => { setFilterDateTo(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:ring-2 focus:ring-accent focus:border-accent"
              />
            </div>
          </div>
          {hasActiveFilters && (
            <div className="mt-3 flex justify-end">
              <button
                onClick={clearFilters}
                className="text-xs text-accent hover:text-accent/80 font-medium transition-colors"
              >
                Effacer les filtres
              </button>
            </div>
          )}
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden p-0">
        {loading ? (
          <LoadingSpinner message="Chargement des logs..." />
        ) : items.length === 0 ? (
          <EmptyState
            icon={FileSearch}
            title="Aucun log trouve"
            description="Aucune entree d'audit ne correspond aux criteres selectionnes."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Provider
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Modele
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Sensibilite
                  </th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Tokens
                  </th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Cout
                  </th>
                  <th className="text-center py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Valide
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {items.map((item) => (
                  <tr
                    key={item.id}
                    className="hover:bg-neutral-50 transition-colors cursor-pointer"
                    onClick={() => setExpandedRow(expandedRow === item.id ? null : item.id)}
                  >
                    <td className="py-3 px-4 text-neutral-600 whitespace-nowrap text-xs">
                      {item.created_at ? new Date(item.created_at).toLocaleString("fr-BE", {
                        day: "2-digit",
                        month: "2-digit",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      }) : "-"}
                    </td>
                    <td className="py-3 px-4 font-medium text-neutral-900 capitalize whitespace-nowrap">
                      {item.provider}
                    </td>
                    <td className="py-3 px-4 text-neutral-600 font-mono text-xs whitespace-nowrap">
                      {item.model}
                    </td>
                    <td className="py-3 px-4">
                      <SensitivityBadge sensitivity={item.data_sensitivity} />
                    </td>
                    <td className="py-3 px-4 text-right text-neutral-600 font-mono text-xs whitespace-nowrap">
                      {(item.token_count_input ?? 0).toLocaleString("fr-BE")} / {(item.token_count_output ?? 0).toLocaleString("fr-BE")}
                    </td>
                    <td className="py-3 px-4 text-right text-neutral-900 font-mono text-xs font-medium whitespace-nowrap">
                      {(item.cost_estimate_eur ?? 0).toFixed(4)} EUR
                    </td>
                    <td className="py-3 px-4 text-center">
                      {item.human_validated ? (
                        <CheckCircle2 className="w-4 h-4 text-green-500 mx-auto" />
                      ) : (
                        <span className="w-4 h-4 block mx-auto text-neutral-300">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {total > perPage && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-neutral-200 bg-neutral-50">
            <p className="text-xs text-neutral-500">
              Page {page} sur {totalPages} ({total} resultats)
            </p>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-1.5 rounded-md bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              {/* Page numbers */}
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum: number;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (page <= 3) {
                  pageNum = i + 1;
                } else if (page >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = page - 2 + i;
                }
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={`w-8 h-8 rounded-md text-xs font-medium transition-colors ${
                      pageNum === page
                        ? "bg-accent text-white"
                        : "bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-50"
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="p-1.5 rounded-md bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Stats
// ---------------------------------------------------------------------------

function StatsTab({ token, tenantId }: { token: string; tenantId?: string }) {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [periodDays, setPeriodDays] = useState(30);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<StatsResponse>(`/llm/audit/stats?days=${periodDays}`, token, { tenantId });
      setStats(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token, tenantId, periodDays]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  if (loading) return <LoadingSpinner message="Calcul des statistiques..." />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-base font-semibold text-neutral-900 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-accent" />
          Statistiques d'utilisation
        </h2>
        <div className="flex items-center gap-2">
          <select
            value={periodDays}
            onChange={(e) => setPeriodDays(Number(e.target.value))}
            className="px-3 py-1.5 text-sm border border-neutral-300 rounded-md bg-white focus:ring-2 focus:ring-accent focus:border-accent"
          >
            <option value={7}>7 derniers jours</option>
            <option value={30}>30 derniers jours</option>
            <option value={90}>90 derniers jours</option>
            <option value={365}>12 derniers mois</option>
          </select>
          <button
            onClick={fetchStats}
            disabled={loading}
            className="px-3 py-1.5 text-sm font-medium text-neutral-600 bg-neutral-100 rounded-md hover:bg-neutral-200 transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={fetchStats} />}

      {stats && (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="card">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-neutral-900">
                    {stats.total_requests.toLocaleString("fr-BE")}
                  </p>
                  <p className="text-xs text-neutral-500">Requetes totales</p>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-green-50 flex items-center justify-center">
                  <DollarSign className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-neutral-900">
                    {stats.total_cost_eur.toFixed(2)} EUR
                  </p>
                  <p className="text-xs text-neutral-500">Cout total</p>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-neutral-900">
                    {stats.human_validated_count.toLocaleString("fr-BE")}
                  </p>
                  <p className="text-xs text-neutral-500">Validations humaines</p>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
                  <Shield className="w-5 h-5 text-accent" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-neutral-900">
                    {stats.human_validation_rate.toFixed(1)}%
                  </p>
                  <p className="text-xs text-neutral-500">Taux de validation</p>
                </div>
              </div>
            </div>
          </div>

          {/* By Provider */}
          <div className="card">
            <h3 className="text-sm font-semibold text-neutral-900 mb-4 flex items-center gap-2">
              <Server className="w-4 h-4 text-accent" />
              Utilisation par provider
            </h3>
            {stats.by_provider.length === 0 ? (
              <p className="text-sm text-neutral-500 text-center py-4">Aucune donnee disponible</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-neutral-200">
                      <th className="text-left py-2.5 px-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Provider
                      </th>
                      <th className="text-right py-2.5 px-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Requetes
                      </th>
                      <th className="text-right py-2.5 px-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Cout total
                      </th>
                      <th className="text-right py-2.5 px-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Moy. input
                      </th>
                      <th className="text-right py-2.5 px-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                        Moy. output
                      </th>
                      <th className="text-left py-2.5 px-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider w-48">
                        Part
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-100">
                    {stats.by_provider.map((ps) => {
                      const pct = stats.total_requests > 0
                        ? (ps.count / stats.total_requests) * 100
                        : 0;
                      return (
                        <tr key={ps.provider} className="hover:bg-neutral-50 transition-colors">
                          <td className="py-2.5 px-3 font-medium text-neutral-900 capitalize">
                            {ps.provider}
                          </td>
                          <td className="py-2.5 px-3 text-right text-neutral-700 font-mono">
                            {ps.count.toLocaleString("fr-BE")}
                          </td>
                          <td className="py-2.5 px-3 text-right text-neutral-700 font-mono">
                            {ps.cost_eur.toFixed(4)} EUR
                          </td>
                          <td className="py-2.5 px-3 text-right text-neutral-500 font-mono text-xs">
                            {(ps.tokens_in || 0).toLocaleString("fr-BE")}
                          </td>
                          <td className="py-2.5 px-3 text-right text-neutral-500 font-mono text-xs">
                            {(ps.tokens_out || 0).toLocaleString("fr-BE")}
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="flex items-center gap-2">
                              <div className="flex-1 h-2 bg-neutral-200 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-accent rounded-full transition-all duration-500"
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                              <span className="text-xs text-neutral-500 w-12 text-right font-mono">
                                {pct.toFixed(1)}%
                              </span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Sensitivity Distribution */}
          <div className="card">
            <h3 className="text-sm font-semibold text-neutral-900 mb-4 flex items-center gap-2">
              <Shield className="w-4 h-4 text-accent" />
              Distribution par sensibilite
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(stats.by_sensitivity).map(([sensitivity, count]) => {
                const pct = stats.total_requests > 0 ? (count / stats.total_requests) * 100 : 0;
                return (
                  <div
                    key={sensitivity}
                    className={`p-4 rounded-lg border ${
                      SENSITIVITY_COLORS[sensitivity] || "bg-neutral-50 border-neutral-200 text-neutral-700"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`w-2.5 h-2.5 rounded-full ${
                          SENSITIVITY_DOT_COLORS[sensitivity] || "bg-neutral-400"
                        }`}
                      />
                      <span className="text-xs font-semibold uppercase">
                        {SENSITIVITY_LABELS[sensitivity] || sensitivity}
                      </span>
                    </div>
                    <p className="text-2xl font-bold">{count.toLocaleString("fr-BE")}</p>
                    <p className="text-xs opacity-75 mt-0.5">{pct.toFixed(1)}% du total</p>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: DPIA
// ---------------------------------------------------------------------------

function DPIATab({ token, tenantId }: { token: string; tenantId?: string }) {
  const [report, setReport] = useState<DPIAReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<DPIAReport>("/llm/audit/dpia-report", token, { tenantId });
      setReport(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token, tenantId]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  const handleExport = async () => {
    if (!report) return;
    setExporting(true);
    try {
      const jsonStr = JSON.stringify(report, null, 2);
      const blob = new Blob([jsonStr], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dpia-report-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  const RISK_COLORS: Record<string, string> = {
    low: "bg-green-100 text-green-800 border-green-300",
    medium: "bg-yellow-100 text-yellow-800 border-yellow-300",
    high: "bg-orange-100 text-orange-800 border-orange-300",
    critical: "bg-red-100 text-red-800 border-red-300",
  };

  if (loading) return <LoadingSpinner message="Generation du rapport DPIA..." />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-base font-semibold text-neutral-900 flex items-center gap-2">
          <Shield className="w-5 h-5 text-accent" />
          Rapport DPIA (Data Protection Impact Assessment)
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExport}
            disabled={exporting || !report}
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Exporter JSON
          </button>
          <button
            onClick={fetchReport}
            disabled={loading}
            className="px-3 py-1.5 text-sm font-medium text-neutral-600 bg-neutral-100 rounded-md hover:bg-neutral-200 transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            <RefreshCw className="w-4 h-4" />
            Regenerer
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={fetchReport} />}

      {report && (
        <>
          {/* System Classification */}
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-orange-900">Classification AI Act</p>
              <p className="text-xs text-orange-700 mt-1">{report.system_classification}</p>
            </div>
          </div>

          {/* Statistics */}
          <div className="card">
            <h3 className="text-sm font-semibold text-neutral-900 mb-4 flex items-center gap-2">
              <FileText className="w-4 h-4 text-accent" />
              Statistiques
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div className="p-3 bg-neutral-50 rounded-lg text-center">
                <p className="text-xl font-bold text-neutral-900">
                  {report.statistics.total_requests.toLocaleString("fr-BE")}
                </p>
                <p className="text-xs text-neutral-500 mt-0.5">Requetes</p>
              </div>
              <div className="p-3 bg-neutral-50 rounded-lg text-center">
                <p className="text-xl font-bold text-neutral-900">
                  {report.statistics.anonymization_rate.toFixed(1)}%
                </p>
                <p className="text-xs text-neutral-500 mt-0.5">Taux anonymisation</p>
              </div>
              <div className="p-3 bg-neutral-50 rounded-lg text-center">
                <p className="text-xl font-bold text-neutral-900">
                  {report.statistics.total_cost_eur.toFixed(2)} EUR
                </p>
                <p className="text-xs text-neutral-500 mt-0.5">Cout total</p>
              </div>
              <div className="p-3 bg-neutral-50 rounded-lg text-center">
                <p className="text-xl font-bold text-neutral-900">
                  {report.statistics.human_validation_rate.toFixed(1)}%
                </p>
                <p className="text-xs text-neutral-500 mt-0.5">Validation humaine</p>
              </div>
            </div>

            {/* Sub-processors */}
            <div className="mt-4 pt-4 border-t border-neutral-200">
              <p className="text-xs font-medium text-neutral-500 mb-2 uppercase">Sous-traitants utilises</p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(report.sub_processors).map(([key, info]: [string, any]) => (
                  <span
                    key={key}
                    className="px-2 py-0.5 bg-accent/10 text-accent rounded text-xs font-medium"
                  >
                    {info.name || key}
                  </span>
                ))}
              </div>
            </div>

            {/* Sensitivity distribution */}
            <div className="mt-4 pt-4 border-t border-neutral-200">
              <p className="text-xs font-medium text-neutral-500 mb-2 uppercase">Distribution de sensibilite</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(report.statistics.usage_by_sensitivity).map(([sens, count]) => (
                  <div key={sens} className="flex items-center gap-1.5">
                    <SensitivityBadge sensitivity={sens} />
                    <span className="text-xs text-neutral-600 font-mono">{(count as number).toLocaleString("fr-BE")}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Risk Assessment */}
          <div className="card">
            <h3 className="text-sm font-semibold text-neutral-900 mb-4 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-accent" />
              Evaluation des risques
            </h3>
            <div
              className="inline-flex items-center px-3 py-1.5 rounded-lg border text-sm font-semibold mb-4 bg-green-100 text-green-800 border-green-300"
            >
              Risque residuel : {report.risk_assessment.residual_risk}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-semibold text-neutral-600 uppercase mb-2">Risques identifies</p>
                <ul className="space-y-1.5">
                  {report.risk_assessment.identified_risks.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-neutral-700">
                      <XCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-xs font-semibold text-neutral-600 uppercase mb-2">Mesures d'attenuation</p>
                <ul className="space-y-1.5">
                  {report.risk_assessment.mitigation_measures.map((m, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-neutral-700">
                      <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* Safeguards */}
          <div className="card">
            <h3 className="text-sm font-semibold text-neutral-900 mb-4 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-accent" />
              Mesures de securite
            </h3>
            <div className="space-y-2">
              {Object.entries(report.safeguards).map(([key, desc]) => (
                <div key={key} className="flex items-start gap-3 text-sm text-neutral-700">
                  <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-medium capitalize">{key.replace(/_/g, " ")}</span>
                    <span className="text-neutral-500"> — {desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Generated at */}
          <div className="text-xs text-neutral-400 text-right">
            Rapport genere le {new Date(report.generated_at).toLocaleString("fr-BE")}
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Configuration
// ---------------------------------------------------------------------------

function ConfigTab({ token, tenantId }: { token: string; tenantId?: string }) {
  const [providers, setProviders] = useState<Record<string, ProviderInfo>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revealedKeys, setRevealedKeys] = useState<Set<string>>(new Set());

  const fetchProviders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ProvidersResponse>("/llm/providers", token, { tenantId });
      setProviders(data.providers || {});
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token, tenantId]);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  const toggleReveal = (name: string) => {
    setRevealedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const maskKey = (name: string) => {
    // We don't have real keys from the API, we just show masked status
    return "sk-****" + "****".repeat(4) + "****";
  };

  if (loading) return <LoadingSpinner message="Chargement de la configuration..." />;

  const providerList = Object.values(providers);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-neutral-900 flex items-center gap-2">
          <Settings className="w-5 h-5 text-accent" />
          Configuration des cles API
        </h2>
        <button
          onClick={fetchProviders}
          disabled={loading}
          className="px-3 py-1.5 text-sm font-medium text-neutral-600 bg-neutral-100 rounded-md hover:bg-neutral-200 transition-colors flex items-center gap-1.5 disabled:opacity-50"
        >
          <RefreshCw className="w-4 h-4" />
          Rafraichir
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={fetchProviders} />}

      {/* Info banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
        <Shield className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-blue-900">Securite des cles API</p>
          <p className="text-xs text-blue-700 mt-1">
            Les cles API sont stockees de maniere chiffree cote serveur. Seul le statut de configuration
            est affiche ici. Pour modifier une cle, utilisez les variables d'environnement du serveur.
          </p>
        </div>
      </div>

      {/* Provider API Keys */}
      <div className="space-y-3">
        {providerList.length === 0 ? (
          <EmptyState
            icon={Key}
            title="Aucun provider configure"
            description="Aucune cle API n'a ete detectee. Configurez les variables d'environnement du serveur."
          />
        ) : (
          providerList.map((provider) => (
            <div key={provider.name} className="card border border-neutral-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      provider.enabled ? "bg-green-50" : "bg-neutral-100"
                    }`}
                  >
                    <Key
                      className={`w-5 h-5 ${provider.enabled ? "text-green-600" : "text-neutral-400"}`}
                    />
                  </div>
                  <div>
                    <h4 className="font-semibold text-neutral-900 capitalize flex items-center gap-2">
                      {provider.name}
                      <TierBadge tier={provider.tier} />
                    </h4>
                    <p className="text-xs text-neutral-500 mt-0.5">
                      Modele par defaut : <span className="font-mono">{provider.default_model}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                      provider.enabled
                        ? "bg-green-100 text-green-700"
                        : "bg-neutral-100 text-neutral-500"
                    }`}
                  >
                    <span
                      className={`w-2 h-2 rounded-full ${
                        provider.enabled ? "bg-green-500" : "bg-neutral-400"
                      }`}
                    />
                    {provider.enabled ? "Configure" : "Non configure"}
                  </span>
                </div>
              </div>

              {/* Masked key display */}
              <div className="mt-3 pt-3 border-t border-neutral-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-neutral-500">Cle API :</span>
                    <code className="text-xs font-mono bg-neutral-100 px-2 py-1 rounded text-neutral-600">
                      {revealedKeys.has(provider.name) ? maskKey(provider.name) : "sk-****...****"}
                    </code>
                  </div>
                  <button
                    onClick={() => toggleReveal(provider.name)}
                    className="p-1.5 text-neutral-400 hover:text-neutral-600 transition-colors"
                    title={revealedKeys.has(provider.name) ? "Masquer" : "Reveler"}
                  >
                    {revealedKeys.has(provider.name) ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* Cost info */}
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div className="p-2 bg-neutral-50 rounded text-center">
                  <p className="text-xs text-neutral-500">Cout input / 1k tokens</p>
                  <p className="text-sm font-semibold text-neutral-900 font-mono">
                    {provider.cost_per_1k_input.toFixed(4)} EUR
                  </p>
                </div>
                <div className="p-2 bg-neutral-50 rounded text-center">
                  <p className="text-xs text-neutral-500">Cout output / 1k tokens</p>
                  <p className="text-sm font-semibold text-neutral-900 font-mono">
                    {provider.cost_per_1k_output.toFixed(4)} EUR
                  </p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Environment Variables Reference */}
      <div className="card bg-neutral-50 border border-neutral-200">
        <h3 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
          <FileText className="w-4 h-4 text-accent" />
          Variables d'environnement requises
        </h3>
        <div className="space-y-1.5">
          {[
            { env: "MISTRAL_API_KEY", desc: "Cle API Mistral AI (Tier 1 - EU-native, France)" },
            { env: "GEMINI_API_KEY", desc: "Cle API Google Gemini (Tier 1 - EU, europe-west1 Belgique)" },
            { env: "ANTHROPIC_API_KEY", desc: "Cle API Anthropic Claude (Tier 1 - EU-US DPF)" },
            { env: "OPENAI_API_KEY", desc: "Cle API OpenAI GPT-4o (Tier 1 - EU-US DPF)" },
            { env: "DEEPSEEK_API_KEY", desc: "Cle API DeepSeek (Tier 2 - Donnees anonymisees uniquement)" },
            { env: "GLM_API_KEY", desc: "Cle API GLM-4 Zhipu (Tier 3 - Donnees publiques uniquement)" },
            { env: "KIMI_API_KEY", desc: "Cle API Kimi Moonshot (Tier 3 - Donnees publiques uniquement)" },
          ].map((item) => (
            <div key={item.env} className="flex items-center gap-3 py-1.5">
              <code className="text-xs font-mono bg-white px-2 py-1 rounded border border-neutral-200 text-neutral-700 min-w-[220px]">
                {item.env}
              </code>
              <span className="text-xs text-neutral-500">{item.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function LLMAdminPage() {
  const { accessToken, tenantId, role } = useAuth();
  const [activeTab, setActiveTab] = useState<TabId>("providers");
  const router = useRouter();

  // Protection: only super_admin can access
  if (role !== "super_admin") {
    return (
      <div className="bg-danger-50 border border-danger-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-danger-900 mb-2">Acces refuse</h2>
        <p className="text-danger-700 text-sm mb-4">
          Vous n'avez pas les permissions pour acceder a cette page.
        </p>
        <button onClick={() => router.push("/dashboard")} className="btn-primary">
          Retour au tableau de bord
        </button>
      </div>
    );
  }

  if (!accessToken) {
    return <LoadingSpinner message="Chargement de la session..." />;
  }

  return (
    <div>
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-neutral-900 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
            <Brain className="w-6 h-6 text-accent" />
          </div>
          LLM Gateway
        </h1>
        <p className="text-neutral-600 mt-2 text-sm">
          Gestion des fournisseurs LLM, audit RGPD, statistiques d'utilisation et analyse d'impact.
        </p>
      </div>

      {/* Tab Navigation - Grid Cards with Icons (matching admin page pattern) */}
      <div className="mb-8">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`p-4 rounded-lg border-2 transition-all duration-200 text-left group ${
                  isActive
                    ? "border-accent bg-accent-50 shadow-md"
                    : "border-neutral-200 bg-white hover:border-accent hover:shadow-subtle"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors ${
                      isActive
                        ? "bg-accent text-white"
                        : "bg-neutral-100 text-neutral-600 group-hover:bg-accent group-hover:text-white"
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p
                      className={`font-semibold transition-colors ${
                        isActive ? "text-neutral-900" : "text-neutral-700 group-hover:text-neutral-900"
                      }`}
                    >
                      {tab.label}
                    </p>
                    <p className="text-xs text-neutral-500 mt-0.5 line-clamp-1">{tab.description}</p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div className="animate-in fade-in duration-200">
        {activeTab === "providers" && <ProvidersTab token={accessToken} tenantId={tenantId} />}
        {activeTab === "audit" && <AuditTab token={accessToken} tenantId={tenantId} />}
        {activeTab === "stats" && <StatsTab token={accessToken} tenantId={tenantId} />}
        {activeTab === "dpia" && <DPIATab token={accessToken} tenantId={tenantId} />}
        {activeTab === "config" && <ConfigTab token={accessToken} tenantId={tenantId} />}
      </div>
    </div>
  );
}
