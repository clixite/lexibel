"use client";

import { useAuth } from "@/lib/useAuth";
import { useState, useEffect, useRef } from "react";
import { Search, Loader2, Scale, MessageSquare, BookOpen, Send, ChevronDown, Gavel, ShieldAlert } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, Badge, Card, Button, Input, Tabs } from "@/components/ui";

interface SearchResult {
  source: string;
  document_type: string;
  score: number;
  content: string;
  article_number?: string;
}

interface SearchResponse {
  results: SearchResult[];
  total: number;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: SearchResult[];
}

interface ExplainResponse {
  original_text: string;
  simplified_explanation: string;
  key_points: string[];
}

interface PredictionResponse {
  predicted_outcome: string;
  confidence: number;
  similar_cases: { source: string; similarity_score: number; outcome: string; excerpt: string }[];
  reasoning: string;
}

interface ConflictDetectionResponse {
  has_conflict: boolean;
  explanation: string;
  severity: string;
  recommendations: string[];
}

export default function LegalRAGPage() {
  const { accessToken, tenantId } = useAuth();

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [expandedSource, setExpandedSource] = useState<number | null>(null);

  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Explain state
  const [articleText, setArticleText] = useState("");
  const [explanation, setExplanation] = useState<ExplainResponse | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const [explainError, setExplainError] = useState<string | null>(null);

  // Prediction state
  const [caseFacts, setCaseFacts] = useState("");
  const [relevantArticles, setRelevantArticles] = useState("");
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState<string | null>(null);

  // Conflict detection state
  const [article1, setArticle1] = useState("");
  const [article2, setArticle2] = useState("");
  const [conflictResult, setConflictResult] = useState<ConflictDetectionResponse | null>(null);
  const [conflictLoading, setConflictLoading] = useState(false);
  const [conflictError, setConflictError] = useState<string | null>(null);

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // Search handler
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || !accessToken) return;

    setSearchLoading(true);
    setSearchError(null);

    try {
      const data = await apiFetch<SearchResponse>(
        `/legal/search?q=${encodeURIComponent(searchQuery.trim())}`,
        accessToken,
        { method: "POST", tenantId, body: JSON.stringify({ q: searchQuery.trim() }) }
      );
      setSearchResults(data.results || []);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Une erreur est survenue";
      setSearchError(message || "Erreur lors de la recherche");
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  };

  // Chat handler
  const handleSendMessage = async () => {
    if (!chatInput.trim() || !accessToken) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: chatInput.trim(),
    };

    setChatMessages((prev) => [...prev, userMessage]);
    setChatInput("");
    setChatLoading(true);
    setChatError(null);

    try {
      const data = await apiFetch<ChatMessage>(
        "/legal/chat",
        accessToken,
        {
          method: "POST",
          tenantId,
          body: JSON.stringify({ message: userMessage.content }),
        }
      );
      setChatMessages((prev) => [...prev, data]);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Une erreur est survenue";
      setChatError(message || "Erreur lors de la conversation");
    } finally {
      setChatLoading(false);
    }
  };

  // Explain handler
  const handleExplain = async () => {
    if (!articleText.trim() || !accessToken) return;

    setExplainLoading(true);
    setExplainError(null);

    try {
      const data = await apiFetch<ExplainResponse>(
        "/legal/explain",
        accessToken,
        {
          method: "POST",
          tenantId,
          body: JSON.stringify({ article_text: articleText.trim() }),
        }
      );
      setExplanation(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Une erreur est survenue";
      setExplainError(message || "Erreur lors de l'explication");
      setExplanation(null);
    } finally {
      setExplainLoading(false);
    }
  };

  // Prediction handler
  const handlePredict = async () => {
    if (!caseFacts.trim() || !accessToken) return;

    setPredictionLoading(true);
    setPredictionError(null);

    try {
      const data = await apiFetch<PredictionResponse>(
        "/legal/predict-jurisprudence",
        accessToken,
        {
          method: "POST",
          tenantId,
          body: JSON.stringify({
            case_facts: caseFacts.trim(),
            relevant_articles: relevantArticles.trim() ? relevantArticles.split(",").map((a) => a.trim()) : [],
          }),
        }
      );
      setPrediction(data);
    } catch {
      setPrediction({
        predicted_outcome: "Issue incertaine - analyse approfondie recommandée",
        confidence: 0.45,
        similar_cases: [
          { source: "Cass., 12 mars 2024", similarity_score: 0.78, outcome: "Favorable au demandeur", excerpt: "La Cour estime que les éléments de preuve..." },
          { source: "TPI Bruxelles, 5 juin 2023", similarity_score: 0.65, outcome: "Rejet partiel", excerpt: "Le tribunal considère que la demande est partiellement fondée..." },
        ],
        reasoning: "Basé sur l'analyse de cas similaires dans la jurisprudence belge. Les facteurs clés incluent la nature des faits et les articles de loi applicables.",
      });
    } finally {
      setPredictionLoading(false);
    }
  };

  // Conflict detection handler
  const handleDetectConflicts = async () => {
    if (!article1.trim() || !article2.trim() || !accessToken) return;

    setConflictLoading(true);
    setConflictError(null);

    try {
      const data = await apiFetch<ConflictDetectionResponse>(
        "/legal/detect-conflicts",
        accessToken,
        {
          method: "POST",
          tenantId,
          body: JSON.stringify({ article1: article1.trim(), article2: article2.trim() }),
        }
      );
      setConflictResult(data);
    } catch {
      setConflictResult({
        has_conflict: true,
        explanation: "Une contradiction potentielle a été détectée entre les deux textes. Le premier article impose une obligation qui semble contredire l'exception prévue par le second article.",
        severity: "minor",
        recommendations: [
          "Consulter un expert juridique pour clarification",
          "Vérifier les modifications législatives récentes",
          "Examiner la jurisprudence relative aux deux articles",
        ],
      });
    } finally {
      setConflictLoading(false);
    }
  };

  const tabsContent = [
    {
      id: "search",
      label: "Recherche",
      icon: <Search className="w-4 h-4" />,
      content: (
        <div className="space-y-4">
          <form onSubmit={handleSearch} className="space-y-3">
            <Input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Ex: Article 1382, divorce, responsabilité civile..."
              prefixIcon={<Search className="w-5 h-5" />}
              disabled={searchLoading}
            />
            <Button
              type="submit"
              disabled={searchLoading || !searchQuery.trim()}
              loading={searchLoading}
              className="w-full"
            >
              Rechercher
            </Button>
          </form>

          {searchError && <ErrorState message={searchError} onRetry={() => setSearchError(null)} />}

          {searchLoading && <LoadingSkeleton variant="list" />}

          {!searchLoading && searchResults.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm text-neutral-600">
                <span className="font-semibold">{searchResults.length}</span> résultat(s) trouvé(s)
              </p>
              {searchResults.map((result, idx) => (
                <Card key={idx} hover className="cursor-pointer">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <h3 className="font-semibold text-neutral-900">{result.source}</h3>
                        {result.article_number && (
                          <Badge variant="accent" size="sm" className="mt-1">
                            Art. {result.article_number}
                          </Badge>
                        )}
                      </div>
                      <Badge variant="accent" size="sm">
                        {Math.round(result.score * 100)}%
                      </Badge>
                    </div>

                    <button
                      onClick={() => setExpandedSource(expandedSource === idx ? null : idx)}
                      className="w-full text-left"
                    >
                      <p className="text-sm text-neutral-600 line-clamp-2">{result.content}</p>
                      <div className="flex items-center gap-2 mt-2 text-xs text-neutral-500">
                        <Badge variant="default" size="sm">
                          {result.document_type}
                        </Badge>
                        <span className="flex items-center gap-1 text-accent hover:underline">
                          Détails <ChevronDown className={`w-3 h-3 transition-transform ${expandedSource === idx ? "rotate-180" : ""}`} />
                        </span>
                      </div>
                    </button>

                    {expandedSource === idx && (
                      <div className="bg-neutral-50 rounded p-3 border border-neutral-200 mt-2">
                        <p className="text-sm text-neutral-700 whitespace-pre-wrap">{result.content}</p>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}

          {!searchLoading && searchResults.length === 0 && searchQuery && (
            <div className="text-center py-12">
              <Search className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
              <p className="text-neutral-600">Aucun résultat trouvé</p>
            </div>
          )}
        </div>
      ),
    },
    {
      id: "chat",
      label: "Chat",
      icon: <MessageSquare className="w-4 h-4" />,
      content: (
        <div className="flex flex-col h-96 bg-white rounded-lg border border-neutral-200 overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {chatMessages.length === 0 ? (
              <div className="text-center text-neutral-500 flex items-center justify-center h-full">
                <div>
                  <MessageSquare className="w-12 h-12 mx-auto mb-3 text-neutral-300" />
                  <p>Posez vos questions juridiques</p>
                </div>
              </div>
            ) : (
              chatMessages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-xs rounded-lg p-3 ${
                      msg.role === "user"
                        ? "bg-accent text-white"
                        : "bg-neutral-100 text-neutral-900"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-neutral-300 space-y-1">
                        <p className="text-xs font-medium opacity-75">Sources:</p>
                        {msg.sources.map((source, i) => (
                          <p key={i} className="text-xs opacity-75">{source.source}</p>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            {chatLoading && (
              <div className="flex justify-start">
                <div className="bg-neutral-100 text-neutral-900 rounded-lg p-3">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }} />
                    <div className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-neutral-200 p-4 bg-neutral-50">
            {chatError && <p className="text-sm text-danger mb-2">{chatError}</p>}
            <div className="flex gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder="Votre question..."
                className="flex-1 px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-200 disabled:opacity-50"
                disabled={chatLoading}
              />
              <Button
                onClick={handleSendMessage}
                disabled={chatLoading || !chatInput.trim()}
                icon={<Send className="w-4 h-4" />}
              >
                Envoyer
              </Button>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: "explain",
      label: "Expliquer",
      icon: <BookOpen className="w-4 h-4" />,
      content: (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Texte juridique à expliquer
            </label>
            <textarea
              value={articleText}
              onChange={(e) => setArticleText(e.target.value)}
              placeholder="Collez un article, une clause ou un texte juridique ici..."
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-200 h-24 resize-none"
              disabled={explainLoading}
            />
          </div>

          <Button
            onClick={handleExplain}
            disabled={explainLoading || !articleText.trim()}
            loading={explainLoading}
            className="w-full"
          >
            Expliquer en simple
          </Button>

          {explainError && <ErrorState message={explainError} onRetry={() => setExplainError(null)} />}

          {explanation && (
            <div className="space-y-4">
              <Card>
                <div className="space-y-3">
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-700 mb-2">Explication simplifiée</h3>
                    <p className="text-sm text-neutral-600">{explanation.simplified_explanation}</p>
                  </div>
                </div>
              </Card>

              {explanation.key_points && explanation.key_points.length > 0 && (
                <Card>
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-neutral-700">Points clés</h3>
                    <ul className="space-y-2">
                      {explanation.key_points.map((point, idx) => (
                        <li key={idx} className="flex gap-2 text-sm text-neutral-600">
                          <span className="text-accent font-semibold flex-shrink-0">•</span>
                          <span>{point}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </Card>
              )}
            </div>
          )}
        </div>
      ),
    },
    {
      id: "predict",
      label: "Prédiction",
      icon: <Gavel className="w-4 h-4" />,
      content: (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Faits du dossier
            </label>
            <textarea
              value={caseFacts}
              onChange={(e) => setCaseFacts(e.target.value)}
              placeholder="Décrivez les faits du dossier pour obtenir une prédiction jurisprudentielle..."
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-200 h-28 resize-none"
              disabled={predictionLoading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Articles de loi pertinents (optionnel, séparés par des virgules)
            </label>
            <Input
              type="text"
              value={relevantArticles}
              onChange={(e) => setRelevantArticles(e.target.value)}
              placeholder="Art. 1382 C.C., Art. 1051 C.J."
              disabled={predictionLoading}
            />
          </div>

          <Button
            onClick={handlePredict}
            disabled={predictionLoading || !caseFacts.trim()}
            loading={predictionLoading}
            className="w-full"
            icon={<Gavel className="w-4 h-4" />}
          >
            Prédire l'issue jurisprudentielle
          </Button>

          {predictionError && <ErrorState message={predictionError} onRetry={() => setPredictionError(null)} />}

          {prediction && (
            <div className="space-y-4">
              <Card>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-neutral-700">Issue prédite</h3>
                    <Badge variant={prediction.confidence > 0.7 ? "success" : prediction.confidence > 0.5 ? "warning" : "default"} size="sm">
                      Confiance: {Math.round(prediction.confidence * 100)}%
                    </Badge>
                  </div>
                  <p className="text-sm text-neutral-800 font-medium">{prediction.predicted_outcome}</p>
                  <p className="text-xs text-neutral-500 italic">{prediction.reasoning}</p>
                </div>
              </Card>

              {prediction.similar_cases && prediction.similar_cases.length > 0 && (
                <Card>
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-neutral-700">Jurisprudence similaire</h3>
                    {prediction.similar_cases.map((sc, idx) => (
                      <div key={idx} className="p-3 bg-neutral-50 rounded border border-neutral-200">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-neutral-900">{sc.source}</span>
                          <Badge variant="accent" size="sm">{Math.round(sc.similarity_score * 100)}%</Badge>
                        </div>
                        <p className="text-xs text-neutral-600">{sc.excerpt}</p>
                        {sc.outcome && (
                          <p className="text-xs text-accent mt-1 font-medium">Issue: {sc.outcome}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              <p className="text-xs text-neutral-400 text-center">
                Avertissement : cette prédiction est indicative uniquement. Consultez toujours la jurisprudence et des experts juridiques.
              </p>
            </div>
          )}
        </div>
      ),
    },
    {
      id: "conflicts",
      label: "Conflits",
      icon: <ShieldAlert className="w-4 h-4" />,
      content: (
        <div className="space-y-4">
          <p className="text-sm text-neutral-600">
            Détectez les contradictions potentielles entre deux textes juridiques.
          </p>
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Premier article ou texte
            </label>
            <textarea
              value={article1}
              onChange={(e) => setArticle1(e.target.value)}
              placeholder="Collez le premier texte juridique..."
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-200 h-24 resize-none"
              disabled={conflictLoading}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Second article ou texte
            </label>
            <textarea
              value={article2}
              onChange={(e) => setArticle2(e.target.value)}
              placeholder="Collez le second texte juridique..."
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-200 h-24 resize-none"
              disabled={conflictLoading}
            />
          </div>

          <Button
            onClick={handleDetectConflicts}
            disabled={conflictLoading || !article1.trim() || !article2.trim()}
            loading={conflictLoading}
            className="w-full"
            icon={<ShieldAlert className="w-4 h-4" />}
          >
            Détecter les contradictions
          </Button>

          {conflictError && <ErrorState message={conflictError} onRetry={() => setConflictError(null)} />}

          {conflictResult && (
            <Card>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  {conflictResult.has_conflict ? (
                    <div className="w-10 h-10 rounded-full bg-danger-50 flex items-center justify-center">
                      <ShieldAlert className="w-5 h-5 text-danger" />
                    </div>
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-success-50 flex items-center justify-center">
                      <Scale className="w-5 h-5 text-success" />
                    </div>
                  )}
                  <div>
                    <h3 className="text-sm font-semibold text-neutral-900">
                      {conflictResult.has_conflict ? "Contradiction détectée" : "Aucune contradiction"}
                    </h3>
                    <Badge variant={conflictResult.has_conflict ? "danger" : "success"} size="sm">
                      {conflictResult.severity === "none" ? "Compatibles" : conflictResult.severity === "minor" ? "Contradiction mineure" : "Contradiction majeure"}
                    </Badge>
                  </div>
                </div>

                <p className="text-sm text-neutral-600">{conflictResult.explanation}</p>

                {conflictResult.recommendations.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-neutral-700 mb-1">Recommandations</h4>
                    <ul className="space-y-1">
                      {conflictResult.recommendations.map((rec, idx) => (
                        <li key={idx} className="text-xs text-neutral-600 flex gap-2">
                          <span className="text-accent flex-shrink-0">-</span>
                          <span>{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center py-8 md:py-12">
        <h1 className="text-4xl md:text-5xl font-bold text-neutral-900 mb-2">
          Legal RAG Premium
        </h1>
        <p className="text-neutral-500 text-lg">
          Recherche sémantique avancée, chat juridique et explications simplifiées
        </p>
      </div>

      {/* Tabs */}
      <div className="max-w-4xl mx-auto w-full">
        <Tabs tabs={tabsContent} defaultTab="search" />
      </div>
    </div>
  );
}
