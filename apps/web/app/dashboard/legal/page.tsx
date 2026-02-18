"use client";

import { useAuth } from "@/lib/useAuth";
import { useState, useEffect, useRef } from "react";
import { Search, Loader2, Scale, MessageSquare, BookOpen, Send, ChevronDown } from "lucide-react";
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
    } catch (err: any) {
      setSearchError(err.message || "Erreur lors de la recherche");
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
    } catch (err: any) {
      setChatError(err.message || "Erreur lors de la conversation");
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
    } catch (err: any) {
      setExplainError(err.message || "Erreur lors de l'explication");
      setExplanation(null);
    } finally {
      setExplainLoading(false);
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
