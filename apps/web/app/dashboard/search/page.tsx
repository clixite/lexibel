"use client";

import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";
import { Search, Loader2, Share2 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, Badge } from "@/components/ui";

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

  const truncateText = (text: string, chars: number = 200): string => {
    if (text.length <= chars) return text;
    return text.substring(0, chars) + "...";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-accent-50 flex items-center justify-center">
          <Search className="w-5 h-5 text-accent" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Recherche IA</h1>
          <p className="text-neutral-500 text-sm">
            Recherche sémantique avancée dans vos documents
          </p>
        </div>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="bg-white rounded-lg shadow-subtle p-4">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Entrez votre requête..."
              className="input pl-10 w-full"
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="btn-primary px-6 flex items-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            Rechercher
          </button>
        </div>
      </form>

      {/* Error State */}
      {error && <ErrorState message={error} onRetry={() => setError(null)} />}

      {/* Results */}
      {searched && !loading && (
        <div>
          {results.length === 0 ? (
            <EmptyState
              title="Aucun résultat"
              message="Aucun document ne correspond à votre recherche. Essayez d'autres termes."
            />
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-neutral-600">
                <span className="font-semibold">{results.length}</span> résultat(s) trouvé(s)
              </p>
              {results.map((result, idx) => (
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
                  <p className="text-sm text-neutral-700 mb-3">
                    {truncateText(result.text)}
                  </p>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="default" size="sm">
                      {result.source}
                    </Badge>
                    <Badge variant="accent" size="sm">
                      {result.case_title}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Loading State */}
      {loading && <LoadingSkeleton variant="list" />}

      {/* Initial Empty State */}
      {!searched && !loading && (
        <EmptyState
          title="Commencez votre recherche"
          message="Utilisez la barre de recherche pour trouver des documents et des informations pertinentes."
        />
      )}
    </div>
  );
}
