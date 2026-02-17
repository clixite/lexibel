"use client";

import { useSession } from "next-auth/react";
import { useState, useEffect, useRef } from "react";
import {
  Search,
  Sparkles,
  Scale,
  FileText,
  MessageSquare,
  BookOpen,
  Loader2,
  Send,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import { useLegalSearch } from "@/lib/hooks/useLegalSearch";
import { useLegalChat } from "@/lib/hooks/useLegalChat";
import { useExplainArticle } from "@/lib/hooks/useExplainArticle";
import type {
  LegalChatMessage,
  LegalSearchParams,
} from "@/lib/types/legal";

export default function LegalRAGPage() {
  const { data: session } = useSession();
  const user = session?.user as any;
  const token = user?.accessToken;
  const tenantId = user?.tenantId;

  // Tab state
  const [activeTab, setActiveTab] = useState<"search" | "chat" | "explain">("search");

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [searchParams, setSearchParams] = useState<LegalSearchParams>({
    q: "",
    limit: 10,
    enable_reranking: true,
    enable_multilingual: true,
  });

  // Chat state
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<LegalChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Explain state
  const [articleText, setArticleText] = useState("");
  const [simplificationLevel, setSimplificationLevel] = useState<"basic" | "medium" | "detailed">("medium");
  const [explanation, setExplanation] = useState<any>(null);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Update search params when debounced query changes
  useEffect(() => {
    if (debouncedQuery) {
      setSearchParams((prev) => ({ ...prev, q: debouncedQuery }));
    }
  }, [debouncedQuery]);

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // Hooks
  const searchResults = useLegalSearch(searchParams, token, tenantId);
  const chatMutation = useLegalChat({
    token,
    tenantId,
    onSuccess: (response) => {
      setChatMessages((prev) => [...prev, response.message]);
      setConversationId(response.conversation_id);
      setChatInput("");
    },
  });
  const explainMutation = useExplainArticle({
    token,
    tenantId,
    onSuccess: (response) => {
      setExplanation(response);
    },
  });

  // Handlers
  const handleSearch = () => {
    setSearchParams((prev) => ({ ...prev, q: searchQuery }));
  };

  const handleSendMessage = () => {
    if (!chatInput.trim()) return;

    const userMessage: LegalChatMessage = {
      role: "user",
      content: chatInput,
      timestamp: new Date().toISOString(),
      sources: [],
    };

    setChatMessages((prev) => [...prev, userMessage]);

    chatMutation.mutate({
      message: chatInput,
      conversation_id: conversationId,
    });
  };

  const handleExplain = () => {
    if (!articleText.trim()) return;

    explainMutation.mutate({
      article_text: articleText,
      simplification_level: simplificationLevel,
    });
  };

  const handleJurisdictionChange = (jurisdiction: string) => {
    setSearchParams((prev) => ({
      ...prev,
      jurisdiction: jurisdiction || undefined,
    }));
  };

  const handleDocumentTypeChange = (documentType: string) => {
    setSearchParams((prev) => ({
      ...prev,
      document_type: documentType || undefined,
    }));
  };

  const handleRerankingToggle = (enabled: boolean) => {
    setSearchParams((prev) => ({
      ...prev,
      enable_reranking: enabled,
    }));
  };

  const handleMultilingualToggle = (enabled: boolean) => {
    setSearchParams((prev) => ({
      ...prev,
      enable_multilingual: enabled,
    }));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Scale className="h-10 w-10 text-indigo-600" />
          <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            Recherche Juridique IA
          </h1>
        </div>
        <p className="text-slate-600 text-lg">
          Recherche sémantique avancée dans le droit belge avec IA
        </p>
      </div>

      {/* Main Container */}
      <div className="max-w-7xl mx-auto">
        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab("search")}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all ${
              activeTab === "search"
                ? "bg-white shadow-lg text-indigo-600"
                : "bg-white/50 text-slate-600 hover:bg-white/80"
            }`}
          >
            <Search className="h-5 w-5" />
            Recherche
          </button>
          <button
            onClick={() => setActiveTab("chat")}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all ${
              activeTab === "chat"
                ? "bg-white shadow-lg text-indigo-600"
                : "bg-white/50 text-slate-600 hover:bg-white/80"
            }`}
          >
            <MessageSquare className="h-5 w-5" />
            Assistant IA
          </button>
          <button
            onClick={() => setActiveTab("explain")}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all ${
              activeTab === "explain"
                ? "bg-white shadow-lg text-indigo-600"
                : "bg-white/50 text-slate-600 hover:bg-white/80"
            }`}
          >
            <BookOpen className="h-5 w-5" />
            Expliquer un article
          </button>
        </div>

        {/* Search Tab */}
        {activeTab === "search" && (
          <div className="space-y-6">
            {/* Search Bar */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex gap-4 mb-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && handleSearch()}
                    placeholder="Ex: Article 1382 responsabilité civile, divorce procédure..."
                    className="w-full pl-12 pr-4 py-4 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-lg"
                  />
                </div>
                <button
                  onClick={handleSearch}
                  disabled={searchResults.isLoading || !searchQuery}
                  className="px-8 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:shadow-lg transition-all disabled:opacity-50 font-medium flex items-center gap-2"
                >
                  {searchResults.isLoading && <Loader2 className="h-5 w-5 animate-spin" />}
                  {searchResults.isLoading ? "Recherche..." : "Rechercher"}
                </button>
              </div>

              {/* Filters */}
              <div className="flex gap-4 flex-wrap">
                <select
                  onChange={(e) => handleJurisdictionChange(e.target.value)}
                  value={searchParams.jurisdiction || ""}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-sm"
                >
                  <option value="">Toutes juridictions</option>
                  <option value="federal">Fédéral</option>
                  <option value="wallonie">Wallonie</option>
                  <option value="flandre">Flandre</option>
                  <option value="bruxelles">Bruxelles</option>
                  <option value="eu">UE</option>
                </select>

                <select
                  onChange={(e) => handleDocumentTypeChange(e.target.value)}
                  value={searchParams.document_type || ""}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-sm"
                >
                  <option value="">Tous types</option>
                  <option value="code_civil">Code Civil</option>
                  <option value="code_judiciaire">Code Judiciaire</option>
                  <option value="jurisprudence">Jurisprudence</option>
                  <option value="moniteur_belge">Moniteur Belge</option>
                </select>

                <label className="flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    className="rounded"
                    checked={searchParams.enable_reranking}
                    onChange={(e) => handleRerankingToggle(e.target.checked)}
                  />
                  Re-ranking IA
                </label>

                <label className="flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    className="rounded"
                    checked={searchParams.enable_multilingual}
                    onChange={(e) => handleMultilingualToggle(e.target.checked)}
                  />
                  Multilingue FR/NL
                </label>
              </div>
            </div>

            {/* Features Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white rounded-xl shadow-lg p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-3 bg-indigo-100 rounded-lg">
                    <Sparkles className="h-6 w-6 text-indigo-600" />
                  </div>
                  <h3 className="font-semibold text-lg">Recherche Sémantique</h3>
                </div>
                <p className="text-slate-600">
                  Recherche par sens avec embeddings text-embedding-3-large (1536 dimensions)
                </p>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-3 bg-purple-100 rounded-lg">
                    <Scale className="h-6 w-6 text-purple-600" />
                  </div>
                  <h3 className="font-semibold text-lg">Re-ranking IA</h3>
                </div>
                <p className="text-slate-600">
                  Cross-encoder pour optimiser la pertinence des résultats
                </p>
              </div>

              <div className="bg-white rounded-xl shadow-lg p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-3 bg-blue-100 rounded-lg">
                    <FileText className="h-6 w-6 text-blue-600" />
                  </div>
                  <h3 className="font-semibold text-lg">Citations Précises</h3>
                </div>
                <p className="text-slate-600">
                  Chaque résultat cite ses sources avec numéro d'article et page
                </p>
              </div>
            </div>

            {/* Query expansion info */}
            {searchResults.data?.expanded_query && searchResults.data.expanded_query !== searchResults.data.query && (
              <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                <p className="text-sm text-blue-800">
                  <strong>Requête étendue:</strong> {searchResults.data.expanded_query}
                </p>
              </div>
            )}

            {/* Detected entities */}
            {searchResults.data?.detected_entities && searchResults.data.detected_entities.length > 0 && (
              <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                <p className="text-sm text-purple-800 mb-2">
                  <strong>Entités détectées:</strong>
                </p>
                <div className="flex flex-wrap gap-2">
                  {searchResults.data.detected_entities.map((entity, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-medium"
                    >
                      {entity.entity_type}: {entity.normalized} ({Math.round(entity.confidence * 100)}%)
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Results */}
            {searchResults.data && searchResults.data.results.length > 0 && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold">
                    Résultats ({searchResults.data.total})
                  </h2>
                  <span className="text-sm text-slate-500">
                    Temps de recherche: {searchResults.data.search_time_ms}ms
                  </span>
                </div>

                <div className="space-y-4">
                  {searchResults.data.results.map((result, idx) => (
                    <div
                      key={idx}
                      className="p-4 border border-slate-200 rounded-lg hover:border-indigo-300 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="font-semibold text-lg">{result.source}</h3>
                          <div className="flex gap-2 mt-1 flex-wrap">
                            <span className="px-2 py-1 bg-indigo-100 text-indigo-700 text-xs rounded">
                              {result.document_type}
                            </span>
                            <span className="px-2 py-1 bg-slate-100 text-slate-700 text-xs rounded">
                              {result.jurisdiction}
                            </span>
                            {result.article_number && (
                              <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded">
                                Art. {result.article_number}
                              </span>
                            )}
                            {result.page_number && (
                              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                                Page {result.page_number}
                              </span>
                            )}
                            {result.date_published && (
                              <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">
                                {new Date(result.date_published).toLocaleDateString("fr-BE")}
                              </span>
                            )}
                          </div>
                        </div>
                        <span className="text-sm font-medium text-indigo-600">
                          Score: {(result.score * 100).toFixed(1)}%
                        </span>
                      </div>

                      <p className="text-slate-700 mb-3 leading-relaxed">{result.chunk_text}</p>

                      {result.highlighted_passages?.length > 0 && (
                        <div className="bg-yellow-50 p-3 rounded border border-yellow-200 mb-3">
                          <p className="text-sm font-medium text-yellow-800 mb-1">
                            Passages pertinents:
                          </p>
                          <ul className="list-disc list-inside text-sm text-yellow-900 space-y-1">
                            {result.highlighted_passages.map((passage: string, i: number) => (
                              <li key={i}>{passage}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {result.related_articles?.length > 0 && (
                        <div className="flex items-center gap-2 text-sm text-slate-600 flex-wrap">
                          <span className="font-medium">Articles liés:</span>
                          {result.related_articles.map((art: string) => (
                            <span key={art} className="px-2 py-1 bg-slate-100 rounded">
                              Art. {art}
                            </span>
                          ))}
                        </div>
                      )}

                      {result.url && (
                        <div className="mt-3">
                          <a
                            href={result.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-indigo-600 hover:text-indigo-800 underline"
                          >
                            Voir la source →
                          </a>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Suggested queries */}
            {searchResults.data?.suggested_queries && searchResults.data.suggested_queries.length > 0 && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h3 className="font-semibold mb-3">Recherches suggérées:</h3>
                <div className="flex flex-wrap gap-2">
                  {searchResults.data.suggested_queries.map((query, idx) => (
                    <button
                      key={idx}
                      onClick={() => setSearchQuery(query)}
                      className="px-4 py-2 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 transition-colors text-sm"
                    >
                      {query}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Error state */}
            {searchResults.isError && (
              <div className="bg-red-50 rounded-xl shadow-lg p-6 border border-red-200">
                <div className="flex items-center gap-3">
                  <AlertCircle className="h-6 w-6 text-red-600" />
                  <div>
                    <h3 className="font-semibold text-red-900">Erreur de recherche</h3>
                    <p className="text-sm text-red-700 mt-1">
                      Une erreur est survenue lors de la recherche. Veuillez réessayer.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Empty State */}
            {!searchResults.data && !searchResults.isLoading && !searchResults.isError && (
              <div className="bg-white rounded-xl shadow-lg p-12 text-center">
                <Search className="h-16 w-16 text-slate-300 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-slate-600 mb-2">
                  Commencez votre recherche
                </h3>
                <p className="text-slate-500">
                  Recherchez dans le Code Civil, la jurisprudence, le Moniteur Belge et plus encore
                </p>
              </div>
            )}
          </div>
        )}

        {/* Chat Tab */}
        {activeTab === "chat" && (
          <div className="bg-white rounded-xl shadow-lg flex flex-col" style={{ height: "calc(100vh - 280px)" }}>
            <div className="flex items-center gap-3 p-6 border-b border-slate-200">
              <Sparkles className="h-6 w-6 text-indigo-600" />
              <h2 className="text-2xl font-bold">Assistant Juridique IA</h2>
            </div>

            {/* Chat messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {chatMessages.length === 0 && (
                <div className="text-center py-12">
                  <MessageSquare className="h-16 w-16 text-slate-300 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-slate-600 mb-2">
                    Commencez une conversation
                  </h3>
                  <p className="text-slate-500 mb-6">
                    Posez vos questions juridiques et obtenez des réponses précises avec sources
                  </p>
                  <div className="max-w-2xl mx-auto bg-blue-50 p-4 rounded-lg border border-blue-200">
                    <p className="text-sm text-blue-800 mb-2">
                      <strong>Exemples de questions:</strong>
                    </p>
                    <ul className="text-sm text-blue-700 space-y-1 text-left">
                      <li>• Quels sont les délais pour intenter une action en responsabilité?</li>
                      <li>• Explique-moi l'article 1134 du Code Civil</li>
                      <li>• Jurisprudence récente sur le droit du travail</li>
                    </ul>
                  </div>
                </div>
              )}

              {chatMessages.map((message, idx) => (
                <div
                  key={idx}
                  className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-2xl rounded-lg p-4 ${
                      message.role === "user"
                        ? "bg-indigo-600 text-white"
                        : "bg-slate-100 text-slate-800"
                    }`}
                  >
                    <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-300">
                        <p className="text-xs font-medium mb-2 opacity-80">Sources:</p>
                        <div className="space-y-1">
                          {message.sources.map((source, i) => (
                            <div key={i} className="text-xs opacity-80">
                              • {source.source} - {source.document_type}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {chatMutation.isPending && (
                <div className="flex justify-start">
                  <div className="max-w-2xl bg-slate-100 rounded-lg p-4">
                    <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
                  </div>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            {/* Chat input */}
            <div className="p-6 border-t border-slate-200">
              <div className="flex gap-4">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && !e.shiftKey && handleSendMessage()}
                  placeholder="Posez votre question juridique..."
                  disabled={chatMutation.isPending}
                  className="flex-1 px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent disabled:opacity-50"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={chatMutation.isPending || !chatInput.trim()}
                  className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:shadow-lg transition-all font-medium disabled:opacity-50 flex items-center gap-2"
                >
                  {chatMutation.isPending ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Send className="h-5 w-5" />
                  )}
                  Envoyer
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Explain Tab */}
        {activeTab === "explain" && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex items-center gap-3 mb-6">
                <BookOpen className="h-6 w-6 text-indigo-600" />
                <h2 className="text-2xl font-bold">Expliquer un Article</h2>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Article de loi à expliquer
                  </label>
                  <textarea
                    rows={6}
                    value={articleText}
                    onChange={(e) => setArticleText(e.target.value)}
                    placeholder="Collez l'article de loi ici..."
                    className="w-full px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Niveau de simplification
                  </label>
                  <select
                    value={simplificationLevel}
                    onChange={(e) => setSimplificationLevel(e.target.value as any)}
                    className="w-full px-4 py-3 border border-slate-200 rounded-lg"
                  >
                    <option value="basic">Basique (très simple, avec exemples)</option>
                    <option value="medium">Moyen (clair mais professionnel)</option>
                    <option value="detailed">Détaillé (technique mais accessible)</option>
                  </select>
                </div>

                <button
                  onClick={handleExplain}
                  disabled={explainMutation.isPending || !articleText.trim()}
                  className="w-full px-6 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:shadow-lg transition-all font-medium text-lg disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {explainMutation.isPending && <Loader2 className="h-5 w-5 animate-spin" />}
                  {explainMutation.isPending ? "Génération en cours..." : "Expliquer cet article"}
                </button>
              </div>

              <div className="mt-6 p-4 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border border-indigo-200">
                <p className="text-sm text-indigo-900">
                  <strong>Comment ça marche:</strong> Notre IA analyse l'article et le reformule
                  en langage simple tout en conservant sa précision juridique. Parfait pour expliquer
                  le droit à vos clients.
                </p>
              </div>
            </div>

            {/* Explanation result */}
            {explanation && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <div className="flex items-center gap-2 mb-4">
                  <CheckCircle className="h-6 w-6 text-green-600" />
                  <h3 className="text-xl font-bold">Explication générée</h3>
                </div>

                <div className="space-y-6">
                  <div>
                    <h4 className="font-semibold text-slate-900 mb-2">Texte original:</h4>
                    <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                      <p className="text-slate-700 leading-relaxed">{explanation.original_text}</p>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-semibold text-slate-900 mb-2">Explication simplifiée:</h4>
                    <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-200">
                      <p className="text-slate-800 leading-relaxed">
                        {explanation.simplified_explanation}
                      </p>
                    </div>
                  </div>

                  {explanation.key_points && explanation.key_points.length > 0 && (
                    <div>
                      <h4 className="font-semibold text-slate-900 mb-2">Points clés:</h4>
                      <ul className="space-y-2">
                        {explanation.key_points.map((point: string, idx: number) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="text-indigo-600 font-bold mt-1">•</span>
                            <span className="text-slate-700">{point}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {explanation.related_articles && explanation.related_articles.length > 0 && (
                    <div>
                      <h4 className="font-semibold text-slate-900 mb-2">Articles connexes:</h4>
                      <div className="flex flex-wrap gap-2">
                        {explanation.related_articles.map((article: string, idx: number) => (
                          <span
                            key={idx}
                            className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium"
                          >
                            {article}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Error state */}
            {explainMutation.isError && (
              <div className="bg-red-50 rounded-xl shadow-lg p-6 border border-red-200">
                <div className="flex items-center gap-3">
                  <AlertCircle className="h-6 w-6 text-red-600" />
                  <div>
                    <h3 className="font-semibold text-red-900">Erreur</h3>
                    <p className="text-sm text-red-700 mt-1">
                      Une erreur est survenue lors de la génération de l'explication. Veuillez réessayer.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="max-w-7xl mx-auto mt-12 grid grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <div className="text-3xl font-bold text-indigo-600">1.2M+</div>
          <div className="text-sm text-slate-600 mt-1">Documents indexés</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <div className="text-3xl font-bold text-purple-600">35ms</div>
          <div className="text-sm text-slate-600 mt-1">Temps de recherche</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <div className="text-3xl font-bold text-blue-600">98.5%</div>
          <div className="text-sm text-slate-600 mt-1">Précision citations</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <div className="text-3xl font-bold text-green-600">FR + NL</div>
          <div className="text-sm text-slate-600 mt-1">Multilingue</div>
        </div>
      </div>
    </div>
  );
}
