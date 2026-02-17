"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { Search, Zap, Clock, TrendingUp } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, Badge, Card, Button, Input } from "@/components/ui";

interface SearchResult {
  id: string;
  score: number;
  text: string;
  source: string;
  case_id: string;
  case_title: string;
}

interface SearchResponse {
  results: SearchResult[];
  total: number;
}

export default function SearchPage() {
  const { data: session } = useSession();
  const user = session?.user as any;
  const token = user?.accessToken;
  const tenantId = user?.tenantId;

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !token) return;

    setLoading(true);
    setError(null);
    setSearched(true);

    try {
      const data = await apiFetch<SearchResponse>(
        `/search?q=${encodeURIComponent(query.trim())}&top_k=10`,
        token,
        { method: "POST", tenantId, body: JSON.stringify({ q: query.trim(), top_k: 10 }) }
      );
      setResults(data.results || []);
    } catch (err: any) {
      setError(err.message || "Erreur lors de la recherche");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickSearch = (term: string) => {
    setQuery(term);
    // Trigger search with new query
    setTimeout(() => {
      const formEvent = new Event("submit", { bubbles: true, cancelable: true });
      document.querySelector("form")?.dispatchEvent(formEvent);
    }, 0);
  };

  const truncateText = (text: string, chars: number = 200): string => {
    if (text.length <= chars) return text;
    return text.substring(0, chars) + "...";
  };

  const getCategoryColor = (source: string): "success" | "warning" | "accent" | "danger" | "neutral" => {
    if (source.includes("contract")) return "accent";
    if (source.includes("clause")) return "warning";
    if (source.includes("directive")) return "success";
    if (source.includes("policy")) return "danger";
    return "neutral";
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center py-8 md:py-12">
        <h1 className="text-4xl md:text-5xl font-bold text-neutral-900 mb-2">
          Recherche Juridique
        </h1>
        <p className="text-neutral-500 text-lg">
          Trouvez instantanément les documents et clauses que vous recherchez
        </p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="max-w-3xl mx-auto w-full">
        <div className="relative">
          <Input
            type="text"
            placeholder="Recherchez des contrats, clauses, directives..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            prefixIcon={<Search className="w-5 h-5" />}
            className="text-lg py-3 pr-12"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-accent hover:bg-accent-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg px-4 py-2 transition-colors duration-normal"
          >
            {loading ? (
              <div className="animate-spin h-5 w-5" />
            ) : (
              <Search className="w-5 h-5" />
            )}
          </button>
        </div>
      </form>

      {/* Quick Suggestions */}
      {!searched && (
        <div className="max-w-3xl mx-auto w-full">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: Zap, label: "Contrats", term: "contract" },
              { icon: Clock, label: "Récent", term: "recent" },
              { icon: TrendingUp, label: "Populaire", term: "popular" },
              { icon: Search, label: "Avancé", term: "advanced" },
            ].map(({ icon: Icon, label, term }) => (
              <button
                key={label}
                onClick={() => handleQuickSearch(term)}
                className="flex items-center justify-center gap-2 p-4 bg-white border border-neutral-200 rounded-lg hover:border-accent hover:shadow-md transition-all duration-normal"
              >
                <Icon className="w-4 h-4 text-accent" />
                <span className="text-sm font-medium text-neutral-700">{label}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Error State */}
      {error && <ErrorState message={error} onRetry={() => setError(null)} />}

      {/* Loading State */}
      {loading && <LoadingSkeleton variant="list" />}

      {/* Results */}
      {searched && !loading && (
        <div className="space-y-6">
          {/* Results Header */}
          <div className="max-w-3xl mx-auto w-full">
            {results.length > 0 ? (
              <p className="text-neutral-600">
                Affichage <span className="font-semibold text-neutral-900">{results.length}</span> résultats
                {query && (
                  <>
                    {" "}
                    pour <span className="font-semibold text-accent">"{query}"</span>
                  </>
                )}
              </p>
            ) : null}
          </div>

          {/* Results Cards */}
          {results.length === 0 ? (
            <EmptyState
              title="Aucun résultat"
              description="Aucun document ne correspond à votre recherche. Essayez d'autres termes."
            />
          ) : (
            <div className="max-w-3xl mx-auto w-full space-y-4">
              {results.map((result) => (
                <Card key={result.id} hover className="cursor-pointer group">
                  <div className="space-y-3">
                    {/* Title and Badge */}
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-2">
                        <h3 className="text-lg font-semibold text-neutral-900 group-hover:text-accent transition-colors">
                          {result.source}
                        </h3>
                        <Badge
                          variant={getCategoryColor(result.source)}
                          size="sm"
                        >
                          {result.case_title}
                        </Badge>
                      </div>
                      <Badge variant="accent" size="sm">
                        {Math.round(result.score * 100)}%
                      </Badge>
                    </div>

                    {/* Excerpt */}
                    <p className="text-neutral-600 text-sm leading-relaxed">
                      {truncateText(result.text)}
                    </p>

                    {/* Score Bar */}
                    <div className="flex items-center gap-3 pt-2">
                      <div className="flex-1">
                        <div className="h-2 bg-neutral-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-accent-400 to-accent-600 transition-all duration-300"
                            style={{ width: `${result.score * 100}%` }}
                          />
                        </div>
                      </div>
                      <span className="text-sm font-medium text-neutral-600">
                        {Math.round(result.score * 100)}%
                      </span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Initial Empty State */}
      {!searched && !loading && !error && (
        <EmptyState
          title="Commencez votre recherche"
          description="Utilisez la barre de recherche pour trouver des documents et des informations pertinentes."
        />
      )}
    </div>
  );
}
