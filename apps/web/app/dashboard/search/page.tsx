"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { Search, Loader2, FileText, Briefcase, Filter } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface SearchResult {
  chunk_text: string;
  document_id: string | null;
  case_id: string | null;
  score: number;
  page_number: number | null;
  source_type: string | null;
}

interface SearchApiResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export default function SearchPage() {
  const { data: session } = useSession();
  const [query, setQuery] = useState("");
  const [caseId, setCaseId] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  const handleSearch = async () => {
    const token = (session?.user as any)?.accessToken;
    if (!token || !query.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { query: query.trim(), top_k: 20 };
      if (caseId.trim()) body.case_id = caseId.trim();

      const data = await apiFetch<SearchApiResponse>("/search", token, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setResults(data.results);
      setTotal(data.total);
      setHasSearched(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const highlightMatch = (text: string) => {
    if (!query.trim()) return text;
    const words = query.trim().split(/\s+/).filter(Boolean);
    const pattern = new RegExp(`(${words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
    const parts = text.split(pattern);
    return parts.map((part, i) =>
      pattern.test(part) ? (
        <mark key={i} className="bg-warning-100 text-warning-800 rounded px-0.5">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">Recherche</h1>
        <p className="text-neutral-500 text-sm mt-1">
          Recherche full-text dans vos dossiers, documents et interactions.
        </p>
      </div>

      {/* Search bar */}
      <div className="bg-white rounded-lg shadow-subtle p-4 mb-6">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Rechercher des dossiers, documents, contacts..."
              className="input pl-11 text-base"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`btn-secondary flex items-center gap-2 ${showFilters ? "bg-neutral-100" : ""}`}
          >
            <Filter className="w-4 h-4" />
            Filtres
          </button>
          <button
            onClick={handleSearch}
            disabled={!query.trim() || loading}
            className="btn-primary flex items-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            Rechercher
          </button>
        </div>

        {/* Filters panel */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t border-neutral-200">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Filtrer par dossier (ID)
                </label>
                <input
                  type="text"
                  value={caseId}
                  onChange={(e) => setCaseId(e.target.value)}
                  placeholder="UUID du dossier (optionnel)"
                  className="input"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {hasSearched && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-neutral-500">
              <span className="font-medium text-neutral-900">{total}</span>{" "}
              r&eacute;sultat{total !== 1 ? "s" : ""}
            </p>
          </div>

          {results.length === 0 ? (
            <div className="bg-white rounded-lg shadow-subtle px-6 py-16 text-center">
              <Search className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
              <p className="text-neutral-500 font-medium">
                Aucun r&eacute;sultat
              </p>
              <p className="text-neutral-400 text-sm mt-1">
                Essayez d&apos;autres termes ou modifiez vos filtres.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {results.map((r, i) => (
                <div
                  key={i}
                  className="bg-white rounded-lg shadow-subtle p-5 hover:shadow-medium transition-shadow duration-150"
                >
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-md bg-accent-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                      {r.source_type === "document" ? (
                        <FileText className="w-5 h-5 text-accent" />
                      ) : (
                        <Briefcase className="w-5 h-5 text-accent" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-neutral-800 leading-relaxed">
                        {highlightMatch(r.chunk_text)}
                      </p>
                      <div className="flex flex-wrap items-center gap-3 mt-3">
                        {r.case_id && (
                          <span className="inline-flex items-center gap-1 text-xs text-neutral-500">
                            <Briefcase className="w-3 h-3" />
                            {r.case_id.slice(0, 8)}...
                          </span>
                        )}
                        {r.document_id && (
                          <span className="inline-flex items-center gap-1 text-xs text-neutral-500">
                            <FileText className="w-3 h-3" />
                            {r.document_id.slice(0, 8)}...
                          </span>
                        )}
                        {r.page_number && (
                          <span className="text-xs text-neutral-400">
                            p. {r.page_number}
                          </span>
                        )}
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-neutral-100 text-neutral-600">
                          {Math.round(r.score * 100)}% pertinence
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Initial state */}
      {!hasSearched && !loading && (
        <div className="bg-white rounded-lg shadow-subtle px-6 py-16 text-center">
          <div className="w-16 h-16 rounded-lg bg-accent-50 flex items-center justify-center mx-auto mb-5">
            <Search className="w-8 h-8 text-accent" />
          </div>
          <h2 className="text-lg font-semibold text-neutral-900 mb-2">
            Recherche globale
          </h2>
          <p className="text-neutral-500 text-sm max-w-md mx-auto">
            Saisissez un terme pour rechercher dans vos dossiers, documents,
            contacts et interactions.
          </p>
        </div>
      )}
    </div>
  );
}
