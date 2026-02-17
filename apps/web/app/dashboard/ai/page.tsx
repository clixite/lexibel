"use client";

import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";
import { Brain, Loader2, FileText, Sparkles, Zap, BarChart3 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, Badge, Card, Button, Input } from "@/components/ui";

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
                    <div className="bg-neutral-50 rounded-lg p-4 max-h-64 overflow-y-auto border border-neutral-200">
                      <p className="text-sm text-neutral-700 whitespace-pre-wrap">
                        {result.result}
                      </p>
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
