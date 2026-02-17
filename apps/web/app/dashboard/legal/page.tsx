"use client";

import { useSession } from "next-auth/react";
import { useState, useEffect, useRef } from "react";
import { Search, Loader2, Scale, MessageSquare, BookOpen, Send } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, Badge } from "@/components/ui";

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

export default function LegalRAGPage() {
  const { data: session } = useSession();
  const user = session?.user as any;
  const token = user?.accessToken;
  const tenantId = user?.tenantId;

  const [activeTab, setActiveTab] = useState<"search" | "chat" | "explain">("search");

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

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

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // Search handler
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || !token) return;

    setSearchLoading(true);
    setSearchError(null);

    try {
      const data = await apiFetch<SearchResponse>(
        `/legal/search?q=${encodeURIComponent(searchQuery.trim())}`,
        token,
        { method: "POST", tenantId, body: JSON.stringify({ q: searchQuery.trim() }) }
      );
      setSearchResults(data.results || []);
    } catch (err: any) {
      setSearchError(err.message || "Erreur lors de la recherche");
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  };

  // Chat handler
  const handleSendMessage = async () => {
    if (!chatInput.trim() || !token) return;

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
        token,
        {
          method: "POST",
          tenantId,
          body: JSON.stringify({ message: userMessage.content }),
        }
      );
      setChatMessages((prev) => [...prev, data]);
    } catch (err: any) {
      setChatError(err.message || "Erreur lors de la conversation");
    } finally {
      setChatLoading(false);
    }
  };

  // Explain handler
  const handleExplain = async () => {
    if (!articleText.trim() || !token) return;

    setExplainLoading(true);
    setExplainError(null);

    try {
      const data = await apiFetch<ExplainResponse>(
        "/legal/explain",
        token,
        {
          method: "POST",
          tenantId,
          body: JSON.stringify({ article_text: articleText.trim() }),
        }
      );
      setExplanation(data);
    } catch (err: any) {
      setExplainError(err.message || "Erreur lors de l'explication");
      setExplanation(null);
    } finally {
      setExplainLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-accent-50 flex items-center justify-center">
          <Scale className="w-5 h-5 text-accent" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">
            Recherche Juridique IA
          </h1>
          <p className="text-neutral-500 text-sm">
            Recherche sémantique dans le droit belge
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-neutral-200">
        <button
          onClick={() => setActiveTab("search")}
          className={`px-4 py-2 font-medium transition-colors border-b-2 ${
            activeTab === "search"
              ? "text-accent border-accent"
              : "text-neutral-600 border-transparent hover:text-neutral-900"
          }`}
        >
          <Search className="w-4 h-4 inline mr-2" />
          Recherche
        </button>
        <button
          onClick={() => setActiveTab("chat")}
          className={`px-4 py-2 font-medium transition-colors border-b-2 ${
            activeTab === "chat"
              ? "text-accent border-accent"
              : "text-neutral-600 border-transparent hover:text-neutral-900"
          }`}
        >
          <MessageSquare className="w-4 h-4 inline mr-2" />
          Chat
        </button>
        <button
          onClick={() => setActiveTab("explain")}
          className={`px-4 py-2 font-medium transition-colors border-b-2 ${
            activeTab === "explain"
              ? "text-accent border-accent"
              : "text-neutral-600 border-transparent hover:text-neutral-900"
          }`}
        >
          <BookOpen className="w-4 h-4 inline mr-2" />
          Expliquer
        </button>
      </div>

      {/* Search Tab */}
      {activeTab === "search" && (
        <div className="space-y-4">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Ex: Article 1382, divorce, responsabilité civile..."
                className="input pl-10 w-full"
                disabled={searchLoading}
              />
            </div>
            <button
              type="submit"
              disabled={searchLoading || !searchQuery.trim()}
              className="btn-primary px-6 flex items-center gap-2"
            >
              {searchLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              Rechercher
            </button>
          </form>

          {searchError && <ErrorState message={searchError} onRetry={() => setSearchError(null)} />}

          {searchLoading && <LoadingSkeleton variant="list" />}

          {!searchLoading && searchResults.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm text-neutral-600">
                <span className="font-semibold">{searchResults.length}</span> résultat(s)
              </p>
              {searchResults.map((result, idx) => (
                <div
                  key={idx}
                  className="bg-white rounded-lg shadow-subtle p-4 hover:shadow-medium transition-shadow"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-neutral-900">{result.source}</h3>
                    <Badge variant="accent" size="sm">
                      {Math.round(result.score * 100)}%
                    </Badge>
                  </div>
                  <p className="text-sm text-neutral-700 mb-2">{result.content}</p>
                  <div className="flex gap-2 flex-wrap">
                    <Badge variant="default" size="sm">
                      {result.document_type}
                    </Badge>
                    {result.article_number && (
                      <Badge variant="accent" size="sm">
                        Art. {result.article_number}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {!searchLoading && searchResults.length === 0 && searchQuery && (
            <div className="bg-white rounded-lg shadow-subtle p-12 text-center">
              <Search className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
              <p className="text-neutral-600">Aucun résultat trouvé</p>
            </div>
          )}
        </div>
      )}

      {/* Chat Tab */}
      {activeTab === "chat" && (
        <div className="bg-white rounded-lg shadow-subtle flex flex-col h-96">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {chatMessages.length === 0 ? (
              <div className="text-center text-neutral-500 pt-8">
                <MessageSquare className="w-12 h-12 mx-auto mb-3 text-neutral-300" />
                <p>Posez vos questions juridiques</p>
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
                    <p className="text-sm">{msg.content}</p>
                  </div>
                </div>
              ))
            )}
            {chatLoading && (
              <div className="flex justify-start">
                <Loader2 className="w-4 h-4 animate-spin text-accent" />
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {chatError && (
            <div className="px-4 py-2 bg-red-50 text-red-700 text-sm">
              {chatError}
            </div>
          )}

          {/* Input */}
          <div className="p-4 border-t border-neutral-200 flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && !e.shiftKey && handleSendMessage()}
              placeholder="Votre question..."
              className="input flex-1"
              disabled={chatLoading}
            />
            <button
              onClick={handleSendMessage}
              disabled={chatLoading || !chatInput.trim()}
              className="btn-primary px-4 flex items-center gap-2"
            >
              {chatLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      )}

      {/* Explain Tab */}
      {activeTab === "explain" && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow-subtle p-4 space-y-3">
            <label className="block text-sm font-medium text-neutral-700">
              Article à expliquer
            </label>
            <textarea
              value={articleText}
              onChange={(e) => setArticleText(e.target.value)}
              placeholder="Collez l'article de loi ici..."
              className="input w-full h-32 resize-none"
              disabled={explainLoading}
            />
            <button
              onClick={handleExplain}
              disabled={explainLoading || !articleText.trim()}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {explainLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <BookOpen className="w-4 h-4" />
              )}
              Expliquer
            </button>
          </div>

          {explainError && <ErrorState message={explainError} onRetry={() => setExplainError(null)} />}

          {explainLoading && <LoadingSkeleton variant="card" />}

          {explanation && (
            <div className="bg-white rounded-lg shadow-subtle p-4 space-y-4">
              <div>
                <h3 className="font-semibold text-neutral-900 mb-2">Explication</h3>
                <p className="text-sm text-neutral-700">
                  {explanation.simplified_explanation}
                </p>
              </div>

              {explanation.key_points && explanation.key_points.length > 0 && (
                <div>
                  <h3 className="font-semibold text-neutral-900 mb-2">Points clés</h3>
                  <ul className="space-y-1">
                    {explanation.key_points.map((point, idx) => (
                      <li key={idx} className="text-sm text-neutral-700 flex gap-2">
                        <span className="text-accent">•</span>
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
