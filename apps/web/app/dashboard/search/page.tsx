"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useRef, useCallback } from "react";
import {
  Search,
  Loader2,
  Briefcase,
  User,
  Mail,
  FileSearch,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import SkeletonList from "@/components/skeletons/SkeletonList";

interface CaseResult {
  id: string;
  reference: string;
  title: string;
  status: string;
  matter_type: string;
}

interface ContactResult {
  id: string;
  full_name: string;
  type: string;
  email: string | null;
  phone_e164: string | null;
}

interface CaseListResponse {
  items: CaseResult[];
  total: number;
}

interface ContactListResponse {
  items: ContactResult[];
  total: number;
}

const STATUS_STYLES: Record<string, string> = {
  open: "bg-success-50 text-success-700",
  in_progress: "bg-accent-50 text-accent-700",
  pending: "bg-warning-50 text-warning-700",
  closed: "bg-neutral-100 text-neutral-600",
};

const STATUS_LABELS: Record<string, string> = {
  open: "Ouvert",
  in_progress: "En cours",
  pending: "En attente",
  closed: "Ferm\u00e9",
};

const TYPE_STYLES: Record<string, string> = {
  natural: "bg-accent-50 text-accent-700",
  legal: "bg-purple-100 text-purple-700",
};

const TYPE_LABELS: Record<string, string> = {
  natural: "Personne physique",
  legal: "Personne morale",
};

export default function SearchPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;

  const [query, setQuery] = useState("");
  const [cases, setCases] = useState<CaseResult[]>([]);
  const [contacts, setContacts] = useState<ContactResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const searchInputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cmd+K / Ctrl+K keyboard shortcut to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const performSearch = useCallback(
    async (searchQuery: string) => {
      if (!token || !searchQuery.trim()) {
        setCases([]);
        setContacts([]);
        setHasSearched(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const q = searchQuery.trim();

        const [casesData, contactsData] = await Promise.all([
          apiFetch<CaseListResponse>(`/cases?q=${encodeURIComponent(q)}`, token, {
            tenantId,
          }).catch(() => ({ items: [], total: 0 } as CaseListResponse)),
          apiFetch<ContactListResponse>(
            `/contacts?q=${encodeURIComponent(q)}`,
            token,
            { tenantId }
          ).catch(() => ({ items: [], total: 0 } as ContactListResponse)),
        ]);

        setCases(casesData.items || []);
        setContacts(contactsData.items || []);
        setHasSearched(true);
      } catch (err: any) {
        setError(err.message || "Erreur lors de la recherche");
      } finally {
        setLoading(false);
      }
    },
    [token, tenantId]
  );

  // Debounced search on input change
  const handleQueryChange = (value: string) => {
    setQuery(value);

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      performSearch(value);
    }, 300);
  };

  // Immediate search on Enter
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      performSearch(query);
    }
  };

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((w) => w[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
  };

  const totalResults = cases.length + contacts.length;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-lg bg-accent-50 flex items-center justify-center">
          <Search className="w-5 h-5 text-accent" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Recherche</h1>
          <p className="text-neutral-500 text-sm">
            Recherchez des dossiers, contacts ou documents
          </p>
        </div>
      </div>

      {/* Search bar */}
      <div className="bg-white rounded-lg shadow-subtle p-4 mb-6">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
          <input
            ref={searchInputRef}
            type="text"
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Recherchez des dossiers, contacts ou documents..."
            className="input pl-12 pr-24 text-base w-full"
            autoFocus
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
            {loading && (
              <Loader2 className="w-4 h-4 animate-spin text-accent" />
            )}
            <kbd className="hidden sm:inline-flex items-center gap-0.5 px-2 py-0.5 text-[10px] font-medium text-neutral-400 bg-neutral-100 rounded border border-neutral-200">
              <span className="text-xs">{"\u2318"}</span>K
            </kbd>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {hasSearched && !loading && (
        <div>
          {/* Results count */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-neutral-500">
              <span className="font-medium text-neutral-900">
                {totalResults}
              </span>{" "}
              r&eacute;sultat{totalResults !== 1 ? "s" : ""}
            </p>
          </div>

          {totalResults === 0 ? (
            <div className="bg-white rounded-lg shadow-subtle px-6 py-16 text-center">
              <Search className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
              <p className="text-neutral-600 font-medium">
                Aucun r&eacute;sultat
              </p>
              <p className="text-neutral-400 text-sm mt-1">
                Essayez d&apos;autres termes de recherche.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Dossiers section */}
              {cases.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Briefcase className="w-4 h-4 text-neutral-500" />
                    <h2 className="text-sm font-semibold text-neutral-700 uppercase tracking-wider">
                      Dossiers
                    </h2>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-600">
                      {cases.length}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {cases.map((c) => (
                      <div
                        key={c.id}
                        onClick={() =>
                          router.push(`/dashboard/cases/${c.id}`)
                        }
                        className="bg-white rounded-lg shadow-subtle p-4 hover:shadow-medium transition-shadow duration-150 cursor-pointer"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3">
                            <div className="w-10 h-10 rounded-md bg-accent-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                              <Briefcase className="w-5 h-5 text-accent" />
                            </div>
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs font-mono text-neutral-500">
                                  {c.reference}
                                </span>
                              </div>
                              <p className="text-sm font-medium text-neutral-900">
                                {c.title}
                              </p>
                              {c.matter_type && (
                                <p className="text-xs text-neutral-500 mt-1">
                                  {c.matter_type}
                                </p>
                              )}
                            </div>
                          </div>
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${
                              STATUS_STYLES[c.status] ||
                              "bg-neutral-100 text-neutral-600"
                            }`}
                          >
                            {STATUS_LABELS[c.status] || c.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Contacts section */}
              {contacts.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <User className="w-4 h-4 text-neutral-500" />
                    <h2 className="text-sm font-semibold text-neutral-700 uppercase tracking-wider">
                      Contacts
                    </h2>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-600">
                      {contacts.length}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {contacts.map((c) => (
                      <div
                        key={c.id}
                        onClick={() =>
                          router.push(`/dashboard/contacts/${c.id}`)
                        }
                        className="bg-white rounded-lg shadow-subtle p-4 hover:shadow-medium transition-shadow duration-150 cursor-pointer"
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className={`w-10 h-10 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0 ${
                              c.type === "legal"
                                ? "bg-purple-100 text-purple-700"
                                : "bg-accent-50 text-accent-700"
                            }`}
                          >
                            {getInitials(c.full_name)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-neutral-900">
                              {c.full_name}
                            </p>
                            <div className="flex items-center gap-3 mt-0.5">
                              {c.email && (
                                <span className="flex items-center gap-1 text-xs text-neutral-500 truncate">
                                  <Mail className="w-3 h-3 flex-shrink-0" />
                                  {c.email}
                                </span>
                              )}
                            </div>
                          </div>
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${
                              TYPE_STYLES[c.type] ||
                              "bg-neutral-100 text-neutral-600"
                            }`}
                          >
                            {TYPE_LABELS[c.type] || c.type}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Loading state */}
      {loading && hasSearched && <SkeletonList />}

      {/* Initial empty state (before any search) */}
      {!hasSearched && !loading && (
        <div className="bg-white rounded-lg shadow-subtle px-6 py-16 text-center">
          <div className="w-16 h-16 rounded-lg bg-accent-50 flex items-center justify-center mx-auto mb-5">
            <FileSearch className="w-8 h-8 text-accent" />
          </div>
          <h2 className="text-lg font-semibold text-neutral-900 mb-2">
            Recherche globale
          </h2>
          <p className="text-neutral-500 text-sm max-w-md mx-auto">
            Recherchez des dossiers, contacts ou documents...
          </p>
          <p className="text-neutral-400 text-xs mt-3">
            Appuyez sur{" "}
            <kbd className="px-1.5 py-0.5 text-[10px] font-medium bg-neutral-100 text-neutral-500 rounded border border-neutral-200">
              {"\u2318"}K
            </kbd>{" "}
            pour lancer une recherche rapide
          </p>
        </div>
      )}
    </div>
  );
}
