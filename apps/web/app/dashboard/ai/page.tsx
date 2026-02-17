"use client";

import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";
import { Brain, Loader2, FileText, Sparkles } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, Badge } from "@/components/ui";

interface Case {
  id: string;
  title: string;
}

interface CasesResponse {
  items: Case[];
}

interface AIResult {
  task_type: string;
  result: string;
  timestamp: string;
}

const AI_CARDS = [
  {
    id: "draft",
    title: "Brouillon IA",
    description: "Génère des brouillons de documents juridiques",
    icon: FileText,
    color: "text-accent",
    bgColor: "bg-accent-50",
  },
  {
    id: "summary",
    title: "Résumé",
    description: "Résume automatiquement les documents complexes",
    icon: Sparkles,
    color: "text-warning",
    bgColor: "bg-warning-50",
  },
  {
    id: "analysis",
    title: "Analyse",
    description: "Analyse approfondie des cas et documents",
    icon: Brain,
    color: "text-accent",
    bgColor: "bg-accent-50",
  },
  {
    id: "generation",
    title: "Génération",
    description: "Génère du contenu juridique personnalisé",
    icon: Sparkles,
    color: "text-success",
    bgColor: "bg-success-50",
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
  const [result, setResult] = useState<AIResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [casesLoading, setCasesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

    try {
      const data = await apiFetch<AIResult>(
        "/ai/generate",
        token,
        {
          method: "POST",
          tenantId,
          body: JSON.stringify({
            case_id: selectedCase,
            task_type: taskType,
            prompt: prompt.trim(),
          }),
        }
      );
      setResult(data);
      setPrompt("");
    } catch (err: any) {
      setError(err.message || "Erreur lors de la génération");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-accent-50 flex items-center justify-center">
          <Brain className="w-5 h-5 text-accent" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Hub IA</h1>
          <p className="text-neutral-500 text-sm">
            Outils IA pour votre pratique juridique
          </p>
        </div>
      </div>

      {/* Error */}
      {error && <ErrorState message={error} onRetry={() => setError(null)} />}

      {/* AI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {AI_CARDS.map((card) => (
          <div
            key={card.id}
            className="bg-white rounded-lg shadow-subtle hover:shadow-medium transition-all"
          >
            {/* Card Header - Clickable */}
            <div
              onClick={() =>
                setExpandedCard(expandedCard === card.id ? null : card.id)
              }
              className="p-4 cursor-pointer flex items-start gap-4"
            >
              <div
                className={`w-12 h-12 rounded-md ${card.bgColor} flex items-center justify-center flex-shrink-0`}
              >
                <card.icon className={`w-6 h-6 ${card.color}`} />
              </div>
              <div className="flex-1">
                <h2 className="text-base font-semibold text-neutral-900">
                  {card.title}
                </h2>
                <p className="text-sm text-neutral-500 mt-1">
                  {card.description}
                </p>
              </div>
            </div>

            {/* Expanded Form */}
            {expandedCard === card.id && (
              <div className="border-t border-neutral-200 p-4 space-y-3">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Dossier
                  </label>
                  <select
                    value={selectedCase}
                    onChange={(e) => setSelectedCase(e.target.value)}
                    className="input w-full"
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

                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Prompt
                  </label>
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Décrivez ce que vous voulez générer..."
                    className="input w-full h-24 resize-none"
                    disabled={loading}
                  />
                </div>

                <button
                  onClick={() => handleGenerate(card.id)}
                  disabled={loading || !selectedCase || !prompt.trim()}
                  className="btn-primary w-full flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  Générer
                </button>

                {/* Result */}
                {result && result.task_type === card.id && (
                  <div className="bg-neutral-50 rounded p-3 max-h-48 overflow-y-auto">
                    <p className="text-sm text-neutral-700 whitespace-pre-wrap">
                      {result.result}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
