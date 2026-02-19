"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Search, Bell, ChevronRight, Loader2 } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuthContext } from "@/lib/AuthProvider";
import { apiFetch } from "@/lib/api";

interface TopBarProps {
  sidebarCollapsed: boolean;
}

interface SearchResult {
  id: string;
  type: "case" | "contact" | "document";
  title: string;
  subtitle?: string;
}

const BREADCRUMB_LABELS: Record<string, string> = {
  dashboard: "Tableau de bord",
  cases: "Dossiers",
  contacts: "Contacts",
  documents: "Documents",
  inbox: "Boîte de réception",
  emails: "Emails",
  calendar: "Calendrier",
  calls: "Appels",
  search: "Recherche",
  graph: "Graphe",
  legal: "Juridique",
  ai: "Assistant IA",
  timeline: "Chronologie",
  migration: "Migration",
  sentinel: "SENTINEL",
  billing: "Facturation",
  admin: "Administration",
  settings: "Paramètres",
  conflicts: "Conflits",
  entity: "Entité",
};

export default function TopBar({ sidebarCollapsed }: TopBarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { accessToken } = useAuthContext();
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Cmd+K keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setSearchOpen(false);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  // Focus input when modal opens
  useEffect(() => {
    if (searchOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    } else {
      setQuery("");
      setResults([]);
    }
  }, [searchOpen]);

  // Debounced search
  const doSearch = useCallback(
    async (q: string) => {
      if (!q.trim() || !accessToken) {
        setResults([]);
        return;
      }
      setSearching(true);
      try {
        const data = await apiFetch<{ results: SearchResult[] }>(
          `/search?q=${encodeURIComponent(q)}&limit=10`,
          accessToken,
        );
        setResults(data.results || []);
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    },
    [accessToken],
  );

  const onQueryChange = (value: string) => {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(value), 300);
  };

  const navigateToResult = (result: SearchResult) => {
    setSearchOpen(false);
    const paths: Record<string, string> = {
      case: `/dashboard/cases/${result.id}`,
      contact: `/dashboard/contacts/${result.id}`,
      document: `/dashboard/documents/${result.id}`,
    };
    router.push(paths[result.type] || "/dashboard/search");
  };

  // Breadcrumb from pathname
  const pathSegments = pathname.split("/").filter(Boolean);
  const breadcrumbs = pathSegments.map((segment, index) => ({
    label: BREADCRUMB_LABELS[segment] || segment.charAt(0).toUpperCase() + segment.slice(1),
    href: "/" + pathSegments.slice(0, index + 1).join("/"),
  }));

  return (
    <header
      className={`fixed top-0 right-0 z-20 h-16 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-700 transition-all duration-300 ${
        sidebarCollapsed ? "left-20" : "left-72"
      }`}
    >
      <div className="h-full px-6 flex items-center justify-between">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm">
          {breadcrumbs.map((crumb, index) => (
            <div key={crumb.href} className="flex items-center gap-2">
              {index > 0 && <ChevronRight className="w-3.5 h-3.5 text-neutral-400" />}
              <Link
                href={crumb.href}
                className={`transition-colors duration-150 ${
                  index === breadcrumbs.length - 1
                    ? "font-semibold text-primary"
                    : "text-neutral-600 dark:text-neutral-400 hover:text-primary"
                }`}
              >
                {crumb.label}
              </Link>
            </div>
          ))}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-3">
          {/* Search */}
          <button
            onClick={() => setSearchOpen(!searchOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors duration-150 text-sm text-neutral-500"
            title="Recherche (Cmd+K)"
          >
            <Search className="w-4 h-4" />
            <span className="hidden md:inline">Rechercher...</span>
            <kbd className="hidden md:inline ml-2 px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-xs font-mono">
              {"\u2318"}K
            </kbd>
          </button>

          {/* Notifications */}
          <button className="relative p-2 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors duration-150">
            <Bell className="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
          </button>
        </div>
      </div>

      {/* Search Modal */}
      {searchOpen && (
        <div
          className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-start justify-center pt-20"
          onClick={() => setSearchOpen(false)}
        >
          <div
            className="bg-white dark:bg-neutral-900 rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center px-4 border-b border-neutral-200 dark:border-neutral-700">
              <Search className="w-5 h-5 text-neutral-400 shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => onQueryChange(e.target.value)}
                placeholder="Rechercher des dossiers, contacts, documents..."
                className="w-full px-4 py-4 text-lg border-none outline-none bg-transparent dark:text-white"
                autoFocus
              />
              {searching && <Loader2 className="w-5 h-5 text-neutral-400 animate-spin shrink-0" />}
            </div>

            <div className="max-h-80 overflow-y-auto">
              {results.length > 0 ? (
                <ul className="py-2">
                  {results.map((result) => (
                    <li key={`${result.type}-${result.id}`}>
                      <button
                        onClick={() => navigateToResult(result)}
                        className="w-full text-left px-4 py-3 hover:bg-neutral-50 dark:hover:bg-neutral-800 flex items-center gap-3"
                      >
                        <span className="text-xs font-medium px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 uppercase">
                          {result.type}
                        </span>
                        <div>
                          <div className="font-medium text-neutral-900 dark:text-white">{result.title}</div>
                          {result.subtitle && (
                            <div className="text-sm text-neutral-500">{result.subtitle}</div>
                          )}
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : query.trim() && !searching ? (
                <div className="py-8 text-center text-neutral-500">
                  Aucun résultat pour &ldquo;{query}&rdquo;
                </div>
              ) : !query.trim() ? (
                <div className="py-8 text-center text-neutral-500 text-sm">
                  <p>Tapez pour rechercher dans vos dossiers, contacts et documents</p>
                  <p className="mt-2 text-xs text-neutral-400">Appuyez sur Esc pour fermer</p>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
