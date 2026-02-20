"use client";

import { useEffect, useState, useMemo, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  Shield,
  Filter,
  Search,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertTriangle,
  CheckCircle,
  XCircle,
  FileCheck,
  ShieldAlert,
  Users,
  Calendar,
  Gavel,
  X,
} from "lucide-react";
import {
  sentinelAPI,
  ConflictSummary,
  ConflictStatus,
  ResolutionType,
} from "@/lib/sentinel/api-client";
import SeverityIndicator from "@/components/sentinel/SeverityIndicator";
import { formatDistanceToNow, format } from "date-fns";
import { fr } from "date-fns/locale";

// ══════════════════════════════════════════════════════════════════
// CONFLICT TYPE LABELS (French)
// ══════════════════════════════════════════════════════════════════

const CONFLICT_TYPE_LABELS: Record<string, string> = {
  direct_adversary: "Opposition directe",
  dual_representation: "Double représentation",
  former_client: "Ancien client",
  associate_conflict: "Conflit d'associé",
  organizational: "Organisationnel",
  familial: "Familial",
  business_interest: "Intérêt commercial",
  multi_hop: "Chaîne relationnelle",
  // Existing schema types (fallbacks)
  director_overlap: "Administrateur commun",
  family_tie: "Lien familial",
  indirect_ownership: "Propriété indirecte",
  group_company: "Groupe de sociétés",
  business_partner: "Partenaire commercial",
  historical_conflict: "Historique",
  professional_overlap: "Conseiller commun",
};

function getConflictTypeLabel(type: string): string {
  return CONFLICT_TYPE_LABELS[type] || type;
}

// ══════════════════════════════════════════════════════════════════
// SEVERITY HELPERS
// ══════════════════════════════════════════════════════════════════

function getSeverityColor(score: number): {
  bg: string;
  text: string;
  border: string;
  dot: string;
} {
  if (score >= 81) {
    return {
      bg: "bg-red-100 dark:bg-red-950/30",
      text: "text-red-800 dark:text-red-200",
      border: "border-red-300 dark:border-red-700",
      dot: "bg-red-500",
    };
  }
  if (score >= 61) {
    return {
      bg: "bg-orange-100 dark:bg-orange-950/30",
      text: "text-orange-800 dark:text-orange-200",
      border: "border-orange-300 dark:border-orange-700",
      dot: "bg-orange-500",
    };
  }
  if (score >= 31) {
    return {
      bg: "bg-yellow-100 dark:bg-yellow-950/30",
      text: "text-yellow-800 dark:text-yellow-200",
      border: "border-yellow-300 dark:border-yellow-700",
      dot: "bg-yellow-500",
    };
  }
  return {
    bg: "bg-green-100 dark:bg-green-950/30",
    text: "text-green-800 dark:text-green-200",
    border: "border-green-300 dark:border-green-700",
    dot: "bg-green-500",
  };
}

function getSeverityLabel(score: number): string {
  if (score >= 81) return "Critique";
  if (score >= 61) return "Élevé";
  if (score >= 31) return "Modéré";
  return "Faible";
}

// ══════════════════════════════════════════════════════════════════
// STATUS HELPERS
// ══════════════════════════════════════════════════════════════════

const STATUS_CONFIG: Record<
  string,
  { label: string; bg: string; text: string }
> = {
  active: {
    label: "Actif",
    bg: "bg-red-100 dark:bg-red-900/40",
    text: "text-red-800 dark:text-red-200",
  },
  resolved: {
    label: "Résolu",
    bg: "bg-green-100 dark:bg-green-900/40",
    text: "text-green-800 dark:text-green-200",
  },
  dismissed: {
    label: "Rejeté",
    bg: "bg-gray-100 dark:bg-gray-700",
    text: "text-gray-800 dark:text-gray-200",
  },
};

// ══════════════════════════════════════════════════════════════════
// MOCK DATA (fallback when API is unavailable)
// ══════════════════════════════════════════════════════════════════

const MOCK_CONFLICTS: ConflictSummary[] = [
  {
    id: "mock-1",
    conflict_type: "direct_adversary" as ConflictSummary["conflict_type"],
    severity_score: 85,
    description:
      "Représentation simultanée de parties adverses dans le litige Dupont c/ Martin",
    entities_involved: [
      { id: "e1", name: "Jean Dupont", type: "Person" },
      { id: "e2", name: "Pierre Martin", type: "Person" },
    ],
    detected_at: new Date().toISOString(),
    status: "active",
    resolved_at: null,
  },
  {
    id: "mock-2",
    conflict_type: "historical_conflict" as ConflictSummary["conflict_type"],
    severity_score: 62,
    description:
      "SA Construct était un ancien client dans un dossier similaire (2023)",
    entities_involved: [
      { id: "e3", name: "SA Construct", type: "Company" },
      { id: "e4", name: "SPRL Batiment Plus", type: "Company" },
    ],
    detected_at: new Date(Date.now() - 86400000 * 3).toISOString(),
    status: "active",
    resolved_at: null,
  },
  {
    id: "mock-3",
    conflict_type: "business_partner" as ConflictSummary["conflict_type"],
    severity_score: 41,
    description:
      "Intérêt financier indirect détecté via participation dans Immobilière du Nord SA",
    entities_involved: [
      { id: "e5", name: "Immobilière du Nord SA", type: "Company" },
    ],
    detected_at: new Date(Date.now() - 86400000 * 7).toISOString(),
    status: "active",
    resolved_at: null,
  },
];

// ══════════════════════════════════════════════════════════════════
// RESOLUTION MODAL COMPONENT
// ══════════════════════════════════════════════════════════════════

interface ResolutionModalProps {
  conflict: ConflictSummary;
  onClose: () => void;
  onResolve: (
    conflictId: string,
    resolution: ResolutionType,
    notes?: string
  ) => Promise<void>;
}

function ResolutionModal({
  conflict,
  onClose,
  onResolve,
}: ResolutionModalProps) {
  const [selectedResolution, setSelectedResolution] =
    useState<ResolutionType | null>(null);
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const severityColors = getSeverityColor(conflict.severity_score);

  const resolutionOptions: Array<{
    value: ResolutionType;
    label: string;
    description: string;
    icon: React.ReactNode;
    selectedBorder: string;
  }> = [
    {
      value: "refused",
      label: "Refuser le dossier",
      description:
        "Le cabinet refuse de prendre ce dossier en raison du conflit d'intérêts",
      icon: <XCircle className="w-5 h-5" />,
      selectedBorder: "border-red-500 bg-red-50 dark:bg-red-950/20",
    },
    {
      value: "waiver_obtained",
      label: "Renonciation obtenue",
      description:
        "Les parties ont donné leur consentement écrit et éclairé",
      icon: <FileCheck className="w-5 h-5" />,
      selectedBorder: "border-green-500 bg-green-50 dark:bg-green-950/20",
    },
    {
      value: "false_positive",
      label: "Faux positif",
      description:
        "Le conflit détecté n'en est pas un après vérification manuelle",
      icon: <ShieldAlert className="w-5 h-5" />,
      selectedBorder: "border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20",
    },
  ];

  const handleSubmit = async () => {
    if (!selectedResolution) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await onResolve(conflict.id, selectedResolution, notes || undefined);
      onClose();
    } catch (err) {
      setError("Erreur lors de la résolution du conflit. Veuillez réessayer.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <Gavel className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                Résolution du conflit
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Choisissez la méthode de résolution
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Conflict Summary */}
        <div className="p-6 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-start gap-3">
            <div
              className={`w-3 h-3 rounded-full mt-1.5 flex-shrink-0 ${severityColors.dot}`}
            />
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${severityColors.bg} ${severityColors.text}`}
                >
                  {getConflictTypeLabel(conflict.conflict_type)}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Sévérité : {conflict.severity_score}/100
                </span>
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                {conflict.description}
              </p>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {conflict.entities_involved.map((entity) => (
                  <span
                    key={entity.id}
                    className="inline-flex items-center px-2 py-0.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded text-xs text-gray-700 dark:text-gray-300"
                  >
                    {entity.name}
                    <span className="ml-1 text-gray-400">
                      ({entity.type === "Person" ? "Personne" : "Société"})
                    </span>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Resolution Options */}
        <div className="p-6 space-y-3">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
            Type de résolution :
          </p>

          {resolutionOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => setSelectedResolution(option.value)}
              className={`w-full p-4 border-2 rounded-lg text-left transition-all ${
                selectedResolution === option.value
                  ? option.selectedBorder + " shadow-md"
                  : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
              }`}
            >
              <div className="flex items-start gap-3">
                <div
                  className={`flex-shrink-0 mt-0.5 ${
                    selectedResolution === option.value
                      ? "text-current"
                      : "text-gray-400 dark:text-gray-500"
                  }`}
                >
                  {option.icon}
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-900 dark:text-white mb-0.5">
                    {option.label}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {option.description}
                  </p>
                </div>
                <div
                  className={`w-5 h-5 rounded-full border-2 flex-shrink-0 mt-0.5 flex items-center justify-center transition-colors ${
                    selectedResolution === option.value
                      ? "border-blue-600 bg-blue-600"
                      : "border-gray-300 dark:border-gray-600"
                  }`}
                >
                  {selectedResolution === option.value && (
                    <div className="w-2 h-2 bg-white rounded-full" />
                  )}
                </div>
              </div>
            </button>
          ))}

          {/* Notes Textarea */}
          {selectedResolution && (
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Notes de résolution
                {selectedResolution === "false_positive" && (
                  <span className="text-red-500 ml-1">(obligatoire)</span>
                )}
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
                placeholder="Notes de résolution..."
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              />
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/30">
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="px-5 py-2.5 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors font-medium disabled:opacity-50"
          >
            Annuler
          </button>
          <button
            onClick={handleSubmit}
            disabled={
              !selectedResolution ||
              isSubmitting ||
              (selectedResolution === "false_positive" && !notes.trim())
            }
            className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
            {isSubmitting ? "Résolution en cours..." : "Confirmer"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// CONFLICT CARD COMPONENT
// ══════════════════════════════════════════════════════════════════

interface ConflictCardItemProps {
  conflict: ConflictSummary;
  isHighlighted: boolean;
  onSelect: (conflict: ConflictSummary) => void;
  onResolve: (conflict: ConflictSummary) => void;
}

function ConflictCardItem({
  conflict,
  isHighlighted,
  onSelect,
  onResolve,
}: ConflictCardItemProps) {
  const severityColors = getSeverityColor(conflict.severity_score);
  const statusConfig = STATUS_CONFIG[conflict.status] || STATUS_CONFIG.active;

  return (
    <div
      onClick={() => onSelect(conflict)}
      className={`bg-white dark:bg-gray-800 rounded-lg border transition-all cursor-pointer hover:shadow-lg ${
        isHighlighted
          ? "border-blue-500 dark:border-blue-400 ring-2 ring-blue-200 dark:ring-blue-900"
          : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
      }`}
    >
      {/* Card Header */}
      <div className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            {/* Severity Badge */}
            <div
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ${severityColors.bg} ${severityColors.text} border ${severityColors.border}`}
            >
              <div
                className={`w-2 h-2 rounded-full ${severityColors.dot}`}
              />
              {conflict.severity_score}
            </div>

            {/* Conflict Type Label */}
            <span className="text-sm font-semibold text-gray-900 dark:text-white">
              {getConflictTypeLabel(conflict.conflict_type)}
            </span>
          </div>

          {/* Status Badge */}
          <span
            className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.text}`}
          >
            {statusConfig.label}
          </span>
        </div>

        {/* Description */}
        <p className="text-sm text-gray-700 dark:text-gray-300 mb-4 leading-relaxed">
          {conflict.description}
        </p>

        {/* Entities */}
        <div className="flex items-start gap-2 mb-3">
          <Users className="w-4 h-4 text-gray-400 dark:text-gray-500 mt-0.5 flex-shrink-0" />
          <div className="flex flex-wrap gap-1.5">
            {conflict.entities_involved.map((entity) => (
              <span
                key={entity.id}
                className="inline-flex items-center px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-700 dark:text-gray-300 font-medium"
              >
                {entity.name}
                <span className="ml-1 text-gray-400 dark:text-gray-500 font-normal">
                  {entity.type === "Person" ? "Personne" : "Société"}
                </span>
              </span>
            ))}
          </div>
        </div>

        {/* Severity Bar */}
        <div className="mb-4">
          <SeverityIndicator
            score={conflict.severity_score}
            size="sm"
            showLabel={false}
          />
          <div className="flex items-center justify-between mt-1">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {getSeverityLabel(conflict.severity_score)}
            </span>
            <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">
              {conflict.severity_score}/100
            </span>
          </div>
        </div>

        {/* Footer: Date + Actions */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-700">
          <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
            <Calendar className="w-3.5 h-3.5" />
            <span>
              Détecté{" "}
              {formatDistanceToNow(new Date(conflict.detected_at), {
                addSuffix: true,
                locale: fr,
              })}
            </span>
            <span className="text-gray-300 dark:text-gray-600 mx-1">|</span>
            <span>
              {format(new Date(conflict.detected_at), "dd/MM/yyyy", {
                locale: fr,
              })}
            </span>
          </div>

          {conflict.status === "active" && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onResolve(conflict);
              }}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
            >
              <Gavel className="w-3.5 h-3.5" />
              Résoudre
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// LOADING SKELETON
// ══════════════════════════════════════════════════════════════════

function ConflictCardSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5 animate-pulse">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="h-6 w-12 bg-gray-200 dark:bg-gray-700 rounded-full" />
          <div className="h-5 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
        <div className="h-6 w-16 bg-gray-200 dark:bg-gray-700 rounded-full" />
      </div>
      <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded mb-2" />
      <div className="h-4 w-3/4 bg-gray-200 dark:bg-gray-700 rounded mb-4" />
      <div className="flex gap-2 mb-4">
        <div className="h-5 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
        <div className="h-5 w-28 bg-gray-200 dark:bg-gray-700 rounded" />
      </div>
      <div className="h-2 w-full bg-gray-200 dark:bg-gray-700 rounded mb-4" />
      <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-700">
        <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
        <div className="h-8 w-24 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// MAIN PAGE CONTENT
// ══════════════════════════════════════════════════════════════════

function ConflictsPageContent() {
  const searchParams = useSearchParams();
  const highlightId = searchParams.get("id");

  // Data
  const [conflicts, setConflicts] = useState<ConflictSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isMockData, setIsMockData] = useState(false);

  // Stats
  const [stats, setStats] = useState({ active: 0, resolved: 0, total: 0 });

  // Filters
  const [statusFilter, setStatusFilter] = useState<ConflictStatus | "all">(
    "all"
  );
  const [severityMin, setSeverityMin] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState("");

  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const pageSize = 20;

  // Resolution
  const [conflictToResolve, setConflictToResolve] =
    useState<ConflictSummary | null>(null);
  const [selectedConflict, setSelectedConflict] =
    useState<ConflictSummary | null>(null);

  // ── Load conflicts ──────────────────────────────────────────────

  const loadConflicts = useCallback(async () => {
    setIsLoading(true);
    setIsMockData(false);
    try {
      const response = await sentinelAPI.listConflicts({
        page,
        page_size: pageSize,
        status: statusFilter,
        severity_min: severityMin > 0 ? severityMin : undefined,
      });

      setConflicts(response.conflicts);
      setTotalPages(response.pagination.total_pages);
      setTotalItems(response.pagination.total);
    } catch (error) {
      console.error("Failed to load conflicts, using mock data:", error);
      // Fallback to mock data
      setConflicts(MOCK_CONFLICTS);
      setTotalPages(1);
      setTotalItems(MOCK_CONFLICTS.length);
      setIsMockData(true);
    } finally {
      setIsLoading(false);
    }
  }, [page, statusFilter, severityMin]);

  const loadStats = useCallback(async () => {
    try {
      const [activeRes, resolvedRes, allRes] = await Promise.all([
        sentinelAPI.listConflicts({ status: "active", page_size: 1 }),
        sentinelAPI.listConflicts({ status: "resolved", page_size: 1 }),
        sentinelAPI.listConflicts({ page_size: 1 }),
      ]);
      setStats({
        active: activeRes.pagination.total,
        resolved: resolvedRes.pagination.total,
        total: allRes.pagination.total,
      });
    } catch {
      // When using mock data, calculate from mock
      const active = MOCK_CONFLICTS.filter(
        (c) => c.status === "active"
      ).length;
      const resolved = MOCK_CONFLICTS.filter(
        (c) => c.status === "resolved"
      ).length;
      setStats({
        active,
        resolved,
        total: MOCK_CONFLICTS.length,
      });
    }
  }, []);

  useEffect(() => {
    loadConflicts();
  }, [loadConflicts]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // Highlight conflict from URL param
  useEffect(() => {
    if (highlightId && conflicts.length > 0) {
      const conflict = conflicts.find((c) => c.id === highlightId);
      if (conflict) {
        setSelectedConflict(conflict);
      }
    }
  }, [highlightId, conflicts]);

  // ── Client-side search filter ───────────────────────────────────

  const filteredConflicts = useMemo(() => {
    if (!searchQuery.trim()) return conflicts;
    const query = searchQuery.toLowerCase();
    return conflicts.filter(
      (c) =>
        c.description.toLowerCase().includes(query) ||
        c.entities_involved.some((e) =>
          e.name.toLowerCase().includes(query)
        ) ||
        getConflictTypeLabel(c.conflict_type).toLowerCase().includes(query)
    );
  }, [conflicts, searchQuery]);

  // ── Resolution handler ──────────────────────────────────────────

  const handleResolve = async (
    conflictId: string,
    resolution: ResolutionType,
    notes?: string
  ) => {
    await sentinelAPI.resolveConflict(conflictId, resolution, notes);
    setConflictToResolve(null);
    setSelectedConflict(null);
    loadConflicts();
    loadStats();
  };

  // ══════════════════════════════════════════════════════════════════
  // RENDER
  // ══════════════════════════════════════════════════════════════════

  return (
    <div className="space-y-6">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            Gestion des Conflits
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Détection, analyse et résolution des conflits d'intérêts
          </p>
        </div>

        {isMockData && (
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            <span className="text-xs font-medium text-amber-700 dark:text-amber-300">
              Données de démonstration
            </span>
          </div>
        )}
      </div>

      {/* ── Stats Bar ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 flex items-center gap-4">
          <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
          </div>
          <div>
            <p className="text-2xl font-bold text-red-600 dark:text-red-400">
              {isLoading ? (
                <span className="inline-block h-7 w-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
              ) : (
                stats.active
              )}
            </p>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Actifs
            </p>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 flex items-center gap-4">
          <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
            <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <p className="text-2xl font-bold text-green-600 dark:text-green-400">
              {isLoading ? (
                <span className="inline-block h-7 w-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
              ) : (
                stats.resolved
              )}
            </p>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Résolus
            </p>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 flex items-center gap-4">
          <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {isLoading ? (
                <span className="inline-block h-7 w-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
              ) : (
                stats.total
              )}
            </p>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Total
            </p>
          </div>
        </div>
      </div>

      {/* ── Filters ────────────────────────────────────────────────── */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Filtres
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Status Filter */}
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5 uppercase tracking-wide">
              Statut
            </label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as ConflictStatus | "all");
                setPage(1);
              }}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">Tous</option>
              <option value="active">Actifs</option>
              <option value="resolved">Résolus</option>
              <option value="dismissed">Rejetés</option>
            </select>
          </div>

          {/* Severity Slider */}
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5 uppercase tracking-wide">
              Sévérité minimale : {severityMin}
            </label>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={severityMin}
              onChange={(e) => {
                setSeverityMin(parseInt(e.target.value));
                setPage(1);
              }}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer mt-2"
            />
            <div className="flex justify-between text-xs text-gray-400 dark:text-gray-500 mt-1">
              <span>0</span>
              <span>50</span>
              <span>100</span>
            </div>
          </div>

          {/* Search Box */}
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5 uppercase tracking-wide">
              Recherche
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Rechercher par nom, description, type..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  <X className="w-3.5 h-3.5 text-gray-400" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Conflict Cards ─────────────────────────────────────────── */}
      {isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <ConflictCardSkeleton key={i} />
          ))}
        </div>
      ) : filteredConflicts.length === 0 ? (
        /* ── Empty State ──────────────────────────────────────────── */
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
          <div className="w-20 h-20 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-5">
            <Shield className="w-10 h-10 text-green-600 dark:text-green-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Aucun conflit détecté
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto">
            {searchQuery
              ? `Aucun résultat pour "« ${searchQuery} »". Essayez avec d'autres termes de recherche.`
              : "Tous les dossiers sont conformes aux règles déontologiques. Le système SENTINEL continue de surveiller les conflits potentiels."}
          </p>
        </div>
      ) : (
        <>
          {/* Results count */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {filteredConflicts.length} conflit
              {filteredConflicts.length > 1 ? "s" : ""} trouvé
              {filteredConflicts.length > 1 ? "s" : ""}
              {searchQuery && (
                <span>
                  {" "}
                  pour &laquo; {searchQuery} &raquo;
                </span>
              )}
            </p>
          </div>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredConflicts.map((conflict) => (
              <ConflictCardItem
                key={conflict.id}
                conflict={conflict}
                isHighlighted={selectedConflict?.id === conflict.id}
                onSelect={setSelectedConflict}
                onResolve={setConflictToResolve}
              />
            ))}
          </div>

          {/* ── Pagination ───────────────────────────────────────────── */}
          {totalPages > 1 && (
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between">
              <div className="text-sm text-gray-700 dark:text-gray-300">
                Page {page} sur {totalPages}
                <span className="text-gray-400 dark:text-gray-500 ml-2">
                  ({totalItems} au total)
                </span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Précédent
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 transition-colors"
                >
                  Suivant
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Detail Panel (below cards when conflict selected) ──────── */}
      {selectedConflict && !conflictToResolve && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/30">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              Détails du conflit
            </h3>
            <button
              onClick={() => setSelectedConflict(null)}
              className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          </div>

          <div className="p-5 space-y-5">
            {/* Type + Severity */}
            <div className="flex flex-wrap items-center gap-3">
              {(() => {
                const sc = getSeverityColor(selectedConflict.severity_score);
                return (
                  <span
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-bold ${sc.bg} ${sc.text} border ${sc.border}`}
                  >
                    <div className={`w-2.5 h-2.5 rounded-full ${sc.dot}`} />
                    {selectedConflict.severity_score}/100
                  </span>
                );
              })()}
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 px-3 py-1 rounded-full">
                {getConflictTypeLabel(selectedConflict.conflict_type)}
              </span>
              {(() => {
                const sc =
                  STATUS_CONFIG[selectedConflict.status] ||
                  STATUS_CONFIG.active;
                return (
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${sc.bg} ${sc.text}`}
                  >
                    {sc.label}
                  </span>
                );
              })()}
            </div>

            {/* Description */}
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
                Description
              </p>
              <p className="text-gray-900 dark:text-gray-100 leading-relaxed">
                {selectedConflict.description}
              </p>
            </div>

            {/* Severity Bar */}
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
                Sévérité
              </p>
              <SeverityIndicator score={selectedConflict.severity_score} />
            </div>

            {/* Entities */}
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
                Entités impliquées
              </p>
              <div className="flex flex-wrap gap-2">
                {selectedConflict.entities_involved.map((entity) => (
                  <span
                    key={entity.id}
                    className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm"
                  >
                    <Users className="w-3.5 h-3.5 text-gray-400" />
                    <span className="text-gray-900 dark:text-gray-100 font-medium">
                      {entity.name}
                    </span>
                    <span className="text-gray-500 dark:text-gray-400 text-xs">
                      {entity.type === "Person" ? "Personne" : "Société"}
                    </span>
                  </span>
                ))}
              </div>
            </div>

            {/* Detection Date */}
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1 uppercase tracking-wide">
                Date de détection
              </p>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                {format(
                  new Date(selectedConflict.detected_at),
                  "dd MMMM yyyy 'à' HH:mm",
                  { locale: fr }
                )}
                <span className="text-gray-400 dark:text-gray-500 ml-2">
                  (
                  {formatDistanceToNow(
                    new Date(selectedConflict.detected_at),
                    {
                      addSuffix: true,
                      locale: fr,
                    }
                  )}
                  )
                </span>
              </p>
            </div>

            {/* Resolve Button */}
            {selectedConflict.status === "active" && (
              <div className="pt-2">
                <button
                  onClick={() => setConflictToResolve(selectedConflict)}
                  className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
                >
                  <Gavel className="w-4 h-4" />
                  Résoudre ce conflit
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Resolution Modal ───────────────────────────────────────── */}
      {conflictToResolve && (
        <ResolutionModal
          conflict={conflictToResolve}
          onClose={() => setConflictToResolve(null)}
          onResolve={handleResolve}
        />
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════
// PAGE EXPORT (with Suspense boundary for useSearchParams)
// ══════════════════════════════════════════════════════════════════

export default function ConflictsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      }
    >
      <ConflictsPageContent />
    </Suspense>
  );
}
