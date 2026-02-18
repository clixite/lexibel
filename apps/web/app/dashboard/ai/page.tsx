"use client";

import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";
import { Brain, Loader2, FileText, Sparkles, Zap, BarChart3, ShieldCheck, Eye, EyeOff, CheckCircle2 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, Badge, Card, Button, Input } from "@/components/ui";

interface Case {
  id: string;
  title: string;
}

interface CasesResponse {
  items: Case[];
}

interface LLMResult {
  content: string;
  provider: string;
  model: string;
  sensitivity: string;
  was_anonymized: boolean;
  tokens: { input: number; output: number };
  cost_eur: number;
  latency_ms: number;
  audit_id: string;
  require_human_validation: boolean;
  /** Kept for card-matching purposes */
  task_type?: string;
}

const PROVIDER_LABELS: Record<string, { label: string; flag: string }> = {
  mistral: { label: "Mistral", flag: "\u{1F1EA}\u{1F1FA}" },
  openai: { label: "OpenAI", flag: "\u{1F1FA}\u{1F1F8}" },
  anthropic: { label: "Anthropic", flag: "\u{1F1FA}\u{1F1F8}" },
  azure: { label: "Azure OpenAI", flag: "\u{1F1EA}\u{1F1FA}" },
  cohere: { label: "Cohere", flag: "\u{1F1E8}\u{1F1E6}" },
};

const SENSITIVITY_STYLES: Record<string, { label: string; className: string }> = {
  public: { label: "Public", className: "bg-green-100 text-green-800" },
  internal: { label: "Interne", className: "bg-blue-100 text-blue-800" },
  confidential: { label: "Confidentiel", className: "bg-yellow-100 text-yellow-800" },
  sensitive: { label: "Sensible", className: "bg-orange-100 text-orange-800" },
  restricted: { label: "Restreint", className: "bg-red-100 text-red-800" },
};

const PURPOSE_MAP: Record<string, string> = {
  draft: "document_drafting",
  summary: "document_summary",
  analysis: "case_analysis",
  generation: "content_generation",
};

const AVAILABLE_PROVIDERS = [
  { value: "", label: "Automatique (recommandé)" },
  { value: "mistral", label: "Mistral \u{1F1EA}\u{1F1FA}" },
  { value: "openai", label: "OpenAI \u{1F1FA}\u{1F1F8}" },
  { value: "anthropic", label: "Anthropic \u{1F1FA}\u{1F1F8}" },
  { value: "azure", label: "Azure OpenAI \u{1F1EA}\u{1F1FA}" },
];

const AI_CARDS = [
  {
    id: "draft",
    title: "Brouillon IA",
    description: "Génère des brouillons de documents juridiques avec IA avancée",
    icon: FileText,
    color: "text-accent",
    bgColor: "bg-accent-50",
    placeholder: "Ex: Créer un contrat de service pour un client IT...",
  },
  {
    id: "summary",
    title: "Résumé Intelligent",
    description: "Résume automatiquement les documents complexes en points clés",
    icon: Sparkles,
    color: "text-warning",
    bgColor: "bg-warning-50",
    placeholder: "Ex: Résumez ce contrat en 5 points clés...",
  },
  {
    id: "analysis",
    title: "Analyse Profonde",
    description: "Analyse approfondie des cas et identifie les risques",
    icon: BarChart3,
    color: "text-success",
    bgColor: "bg-success-50",
    placeholder: "Ex: Analysez les risques juridiques de ce contrat...",
  },
  {
    id: "generation",
    title: "Génération Premium",
    description: "Génère du contenu juridique personnalisé et complet",
    icon: Zap,
    color: "text-danger",
    bgColor: "bg-danger-50",
    placeholder: "Ex: Générer une clause de limitation de responsabilité...",
  },
];

export default function AIHubPage() {
  const { data: session } = useSession();
  const user = session?.user as any;
  const token = user?.accessToken;
  const tenantId = user?.tenantId;

  const [cases, setCases] = useState<Case[]>([]);
  const [expandedCard, setExpandedCard] = useState<string | null>(null);
  const [selectedCase, setSelectedCase] = useState("");
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState<LLMResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [casesLoading, setCasesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preferredProvider, setPreferredProvider] = useState("");
  const [validated, setValidated] = useState(false);
  const [validating, setValidating] = useState(false);

  // Load cases on mount
  useEffect(() => {
    if (!token) return;
    setCasesLoading(true);
    apiFetch<CasesResponse>("/cases", token, { tenantId })
      .then((data) => setCases(data.items || []))
      .catch((err) => setError(err.message))
      .finally(() => setCasesLoading(false));
  }, [token, tenantId]);

  const handleGenerate = async (taskType: string) => {
    if (!selectedCase.trim() || !prompt.trim() || !token) {
      setError("Veuillez sélectionner un dossier et entrer un prompt");
      return;
    }

    setLoading(true);
    setError(null);
    setValidated(false);

    try {
      const data = await apiFetch<LLMResult>(
        "/llm/complete",
        token,
        {
          method: "POST",
          tenantId,
          body: JSON.stringify({
            messages: [{ role: "user", content: prompt.trim() }],
            purpose: PURPOSE_MAP[taskType] || "case_analysis",
            preferred_provider: preferredProvider || null,
            temperature: 0.3,
            max_tokens: 4096,
          }),
        }
      );
      setResult({ ...data, task_type: taskType });
      setPrompt("");
    } catch (err: any) {
      setError(err.message || "Erreur lors de la génération");
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async (auditId: string) => {
    if (!token) return;
    setValidating(true);
    try {
      await apiFetch(`/llm/audit/${auditId}/validate`, token, {
        method: "POST",
        tenantId,
      });
      setValidated(true);
    } catch (err: any) {
      setError(err.message || "Erreur lors de la validation");
    } finally {
      setValidating(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center py-8 md:py-12">
        <h1 className="text-4xl md:text-5xl font-bold text-neutral-900 mb-2">
          Hub IA Juridique
        </h1>
        <p className="text-neutral-500 text-lg">
          Outils IA avancés pour accélérer votre pratique juridique
        </p>
      </div>

      {/* Error */}
      {error && <ErrorState message={error} onRetry={() => setError(null)} />}

      {/* AI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto w-full">
        {AI_CARDS.map((card) => (
          <Card
            key={card.id}
            hover
            className={`cursor-pointer transition-all ${expandedCard === card.id ? "ring-2 ring-accent" : ""}`}
            onClick={() =>
              setExpandedCard(expandedCard === card.id ? null : card.id)
            }
          >
            <div className="space-y-4">
              {/* Card Header */}
              <div className="flex items-start gap-4">
                <div
                  className={`w-14 h-14 rounded-lg ${card.bgColor} flex items-center justify-center flex-shrink-0`}
                >
                  <card.icon className={`w-7 h-7 ${card.color}`} />
                </div>
                <div className="flex-1">
                  <h2 className="text-lg font-semibold text-neutral-900">
                    {card.title}
                  </h2>
                  <p className="text-sm text-neutral-500 mt-1">
                    {card.description}
                  </p>
                </div>
              </div>

              {/* Expanded Form */}
              {expandedCard === card.id && (
                <div className="space-y-4 pt-4 border-t border-neutral-200">
                  {/* Case Selector */}
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Dossier
                    </label>
                    <select
                      value={selectedCase}
                      onChange={(e) => setSelectedCase(e.target.value)}
                      className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-200 disabled:opacity-50"
                      disabled={casesLoading || loading}
                    >
                      <option value="">Sélectionner un dossier...</option>
                      {cases.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.title}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Provider Selector */}
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Fournisseur LLM
                    </label>
                    <select
                      value={preferredProvider}
                      onChange={(e) => setPreferredProvider(e.target.value)}
                      className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-200 disabled:opacity-50"
                      disabled={loading}
                    >
                      {AVAILABLE_PROVIDERS.map((p) => (
                        <option key={p.value} value={p.value}>
                          {p.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Textarea */}
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-2">
                      Instructions
                    </label>
                    <textarea
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder={card.placeholder}
                      className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-200 disabled:opacity-50 h-28 resize-none"
                      disabled={loading}
                    />
                  </div>

                  {/* Action Button */}
                  <Button
                    onClick={() => handleGenerate(card.id)}
                    disabled={loading || !selectedCase || !prompt.trim()}
                    loading={loading}
                    className="w-full"
                    icon={<Sparkles className="w-4 h-4" />}
                  >
                    Générer avec IA
                  </Button>

                  {/* Result Display */}
                  {result && result.task_type === card.id && (
                    <div className="bg-neutral-50 rounded-lg p-4 border border-neutral-200 space-y-3">
                      {/* Metadata Badges */}
                      <div className="flex flex-wrap items-center gap-2">
                        {/* Provider Badge */}
                        {result.provider && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                            {PROVIDER_LABELS[result.provider]?.flag || ""}{" "}
                            {PROVIDER_LABELS[result.provider]?.label || result.provider}
                            {result.model && (
                              <span className="text-indigo-500 ml-1">({result.model})</span>
                            )}
                          </span>
                        )}

                        {/* Sensitivity Badge */}
                        {result.sensitivity && (
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                              SENSITIVITY_STYLES[result.sensitivity]?.className ||
                              "bg-gray-100 text-gray-800"
                            }`}
                          >
                            <ShieldCheck className="w-3 h-3" />
                            {SENSITIVITY_STYLES[result.sensitivity]?.label || result.sensitivity}
                          </span>
                        )}

                        {/* Anonymization Indicator */}
                        {result.was_anonymized !== undefined && (
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                              result.was_anonymized
                                ? "bg-purple-100 text-purple-800"
                                : "bg-gray-100 text-gray-600"
                            }`}
                          >
                            {result.was_anonymized ? (
                              <>
                                <EyeOff className="w-3 h-3" />
                                Anonymisé
                              </>
                            ) : (
                              <>
                                <Eye className="w-3 h-3" />
                                Non anonymisé
                              </>
                            )}
                          </span>
                        )}
                      </div>

                      {/* Cost & Performance */}
                      <div className="flex flex-wrap items-center gap-3 text-xs text-neutral-500">
                        {result.cost_eur !== undefined && (
                          <span>
                            {"Coût\u00a0:"} {result.cost_eur < 0.01
                              ? `${(result.cost_eur * 1000).toFixed(2)} m\u20AC`
                              : `${result.cost_eur.toFixed(4)} \u20AC`}
                          </span>
                        )}
                        {result.tokens && (
                          <span>
                            {"Tokens\u00a0:"} {result.tokens.input} in / {result.tokens.output} out
                          </span>
                        )}
                        {result.latency_ms !== undefined && (
                          <span>
                            {"Latence\u00a0:"} {result.latency_ms < 1000
                              ? `${result.latency_ms} ms`
                              : `${(result.latency_ms / 1000).toFixed(1)} s`}
                          </span>
                        )}
                      </div>

                      {/* Generated Content */}
                      <div className="max-h-64 overflow-y-auto">
                        <p className="text-sm text-neutral-700 whitespace-pre-wrap">
                          {result.content}
                        </p>
                      </div>

                      {/* Human Validation (AI Act Art. 14) */}
                      {result.audit_id && (
                        <div className="pt-2 border-t border-neutral-200">
                          {validated ? (
                            <div className="flex items-center gap-2 text-sm text-green-700">
                              <CheckCircle2 className="w-4 h-4" />
                              Réponse validée (Art. 14 AI Act)
                            </div>
                          ) : (
                            <Button
                              onClick={() => handleValidate(result.audit_id)}
                              disabled={validating}
                              loading={validating}
                              className="w-full"
                              icon={<ShieldCheck className="w-4 h-4" />}
                            >
                              Valider cette réponse (Art. 14 AI Act)
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Loading State */}
                  {loading && (
                    <div className="bg-neutral-50 rounded-lg p-4 flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-accent" />
                      <span className="text-sm text-neutral-600">Génération en cours...</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
