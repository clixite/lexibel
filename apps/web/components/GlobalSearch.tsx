"use client";

import { useState, useEffect, useRef } from "react";
import { Search, Briefcase, Users, Calendar, FileText, Loader2, ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";

interface SearchResult {
  id: string;
  type: "case" | "contact" | "event" | "document";
  title: string;
  subtitle?: string;
  href: string;
  icon: React.ReactNode;
}

const mockResults: SearchResult[] = [
  {
    id: "1",
    type: "case",
    title: "DOS-2026-001 - Dupont c/ SA Immobel",
    subtitle: "Dossier en cours",
    href: "/dashboard/cases/1",
    icon: <Briefcase className="w-4 h-4" />,
  },
  {
    id: "2",
    type: "contact",
    title: "Jean Dupont",
    subtitle: "Client - Personne physique",
    href: "/dashboard/contacts/2",
    icon: <Users className="w-4 h-4" />,
  },
];

export default function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  // Open with Ctrl+/ or Cmd+/
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "/" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open]);

  // Search
  useEffect(() => {
    if (!query) {
      setResults([]);
      return;
    }

    setLoading(true);
    // Simulate API call
    setTimeout(() => {
      const filtered = mockResults.filter(
        (r) =>
          r.title.toLowerCase().includes(query.toLowerCase()) ||
          r.subtitle?.toLowerCase().includes(query.toLowerCase())
      );
      setResults(filtered);
      setLoading(false);
      setSelectedIndex(0);
    }, 300);
  }, [query]);

  // Keyboard navigation
  useEffect(() => {
    if (!open) return;

    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => (i + 1) % results.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => (i - 1 + results.length) % results.length);
      } else if (e.key === "Enter" && results[selectedIndex]) {
        e.preventDefault();
        router.push(results[selectedIndex].href);
        setOpen(false);
        setQuery("");
      }
    };

    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, results, selectedIndex, router]);

  if (!open) return null;

  const groupedResults = results.reduce((acc, result) => {
    if (!acc[result.type]) acc[result.type] = [];
    acc[result.type].push(result);
    return acc;
  }, {} as Record<string, SearchResult[]>);

  const typeLabels = {
    case: "Dossiers",
    contact: "Contacts",
    event: "Événements",
    document: "Documents",
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={() => {
        setOpen(false);
        setQuery("");
      }}
    >
      <div className="fixed top-24 left-1/2 -translate-x-1/2 w-full max-w-2xl">
        <div
          className="bg-white rounded-lg shadow-2xl border border-neutral-200 animate-in slide-in-from-top-4 duration-150"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Search Input */}
          <div className="flex items-center gap-3 px-6 py-4 border-b border-neutral-200">
            <Search className="w-5 h-5 text-neutral-400" />
            <input
              ref={inputRef}
              type="text"
              placeholder="Rechercher des dossiers, contacts, événements..."
              className="flex-1 outline-none text-base"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            {loading && <Loader2 className="w-5 h-5 animate-spin text-primary" />}
            <kbd className="px-2.5 py-1 text-xs bg-neutral-100 text-neutral-600 rounded font-mono">
              Esc
            </kbd>
          </div>

          {/* Results */}
          <div className="max-h-96 overflow-y-auto">
            {query && results.length === 0 && !loading ? (
              <div className="px-6 py-12 text-center">
                <p className="text-sm text-neutral-500">Aucun résultat trouvé</p>
                <p className="text-xs text-neutral-400 mt-1">
                  Essayez avec d'autres mots-clés
                </p>
              </div>
            ) : (
              <div>
                {Object.entries(groupedResults).map(([type, items]) => (
                  <div key={type}>
                    <div className="px-6 py-2 text-xs font-semibold text-neutral-500 uppercase tracking-wider bg-neutral-50">
                      {typeLabels[type as keyof typeof typeLabels]}
                    </div>
                    {items.map((result, index) => {
                      const globalIndex = results.indexOf(result);
                      const isSelected = globalIndex === selectedIndex;

                      return (
                        <button
                          key={result.id}
                          onClick={() => {
                            router.push(result.href);
                            setOpen(false);
                            setQuery("");
                          }}
                          className={`w-full flex items-center gap-4 px-6 py-3 transition-colors duration-150 ${
                            isSelected
                              ? "bg-primary/10 text-primary"
                              : "hover:bg-neutral-50"
                          }`}
                        >
                          <div
                            className={`p-2 rounded ${
                              isSelected
                                ? "bg-primary text-white"
                                : "bg-neutral-100 text-neutral-600"
                            }`}
                          >
                            {result.icon}
                          </div>
                          <div className="flex-1 text-left">
                            <p className="text-sm font-medium text-neutral-900">
                              {result.title}
                            </p>
                            {result.subtitle && (
                              <p className="text-xs text-neutral-500">
                                {result.subtitle}
                              </p>
                            )}
                          </div>
                          {isSelected && <ArrowRight className="w-4 h-4" />}
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          {results.length > 0 && (
            <div className="flex items-center justify-between px-6 py-3 border-t border-neutral-200 text-xs text-neutral-500 bg-neutral-50">
              <span>↑↓ naviguer</span>
              <span>⏎ ouvrir</span>
              <span>Esc fermer</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
