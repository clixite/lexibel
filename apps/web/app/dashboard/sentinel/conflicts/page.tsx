"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  Filter,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import {
  sentinelAPI,
  ConflictSummary,
  ConflictStatus,
  ConflictDetail,
  ResolutionType,
} from "@/lib/sentinel/api-client";
import ConflictBadge from "@/components/sentinel/ConflictBadge";
import SeverityIndicator from "@/components/sentinel/SeverityIndicator";
import ConflictResolutionModal from "@/components/sentinel/ConflictResolutionModal";
import SentinelGraphVisualization from "@/components/sentinel/SentinelGraphVisualization";
import { formatDistanceToNow } from "date-fns";
import { fr } from "date-fns/locale";

function ConflictsPageContent() {
  const searchParams = useSearchParams();
  const highlightId = searchParams.get("id");

  const [conflicts, setConflicts] = useState<ConflictSummary[]>([]);
  const [selectedConflict, setSelectedConflict] = useState<ConflictSummary | null>(null);
  const [showResolutionModal, setShowResolutionModal] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [statusFilter, setStatusFilter] = useState<ConflictStatus | "all">("all");
  const [severityMin, setSeverityMin] = useState<number>(0);

  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 20;

  useEffect(() => {
    loadConflicts();
  }, [page, statusFilter, severityMin]);

  useEffect(() => {
    if (highlightId && conflicts.length > 0) {
      const conflict = conflicts.find((c) => c.id === highlightId);
      if (conflict) {
        setSelectedConflict(conflict);
      }
    }
  }, [highlightId, conflicts]);

  const loadConflicts = async () => {
    setIsLoading(true);
    try {
      const response = await sentinelAPI.listConflicts({
        page,
        page_size: pageSize,
        status: statusFilter,
        severity_min: severityMin > 0 ? severityMin : undefined,
      });

      setConflicts(response.conflicts);
      setTotalPages(response.pagination.total_pages);
    } catch (error) {
      console.error("Failed to load conflicts:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResolve = async (resolution: ResolutionType, notes?: string) => {
    if (!selectedConflict) return;

    try {
      await sentinelAPI.resolveConflict(selectedConflict.id, resolution, notes);
      setShowResolutionModal(false);
      setSelectedConflict(null);
      loadConflicts(); // Refresh list
    } catch (error) {
      console.error("Failed to resolve conflict:", error);
      throw error;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Liste des conflits
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Gestion et résolution des conflits d'intérêts détectés
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Filtres
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Status filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Statut
            </label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as ConflictStatus | "all");
                setPage(1);
              }}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">Tous</option>
              <option value="active">Actifs</option>
              <option value="resolved">Résolus</option>
              <option value="dismissed">Rejetés</option>
            </select>
          </div>

          {/* Severity filter */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Sévérité minimale : {severityMin}
            </label>
            <input
              type="range"
              min="0"
              max="100"
              step="10"
              value={severityMin}
              onChange={(e) => {
                setSeverityMin(parseInt(e.target.value));
                setPage(1);
              }}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
              <span>Tous</span>
              <span>50</span>
              <span>100</span>
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : conflicts.length === 0 ? (
          <div className="text-center py-12">
            <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-600 dark:text-gray-400">Aucun conflit trouvé</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Description
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Sévérité
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Statut
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {conflicts.map((conflict) => (
                    <tr
                      key={conflict.id}
                      className={`hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors ${
                        selectedConflict?.id === conflict.id ? "bg-blue-50 dark:bg-blue-950/20" : ""
                      }`}
                      onClick={() => setSelectedConflict(conflict)}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <ConflictBadge type={conflict.conflict_type} />
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900 dark:text-gray-100 max-w-md">
                          {conflict.description}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {conflict.entities_involved.map((e) => e.name).join(" • ")}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="w-24">
                          <SeverityIndicator
                            score={conflict.severity_score}
                            showLabel={false}
                            size="sm"
                          />
                        </div>
                        <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">
                          {conflict.severity_score}/100
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {formatDistanceToNow(new Date(conflict.detected_at), {
                          addSuffix: true,
                          locale: fr,
                        })}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 text-xs font-medium rounded-full ${
                            conflict.status === "active"
                              ? "bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200"
                              : conflict.status === "resolved"
                              ? "bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200"
                              : "bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200"
                          }`}
                        >
                          {conflict.status === "active"
                            ? "Actif"
                            : conflict.status === "resolved"
                            ? "Résolu"
                            : "Rejeté"}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                        {conflict.status === "active" && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedConflict(conflict);
                              setShowResolutionModal(true);
                            }}
                            className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium"
                          >
                            Résoudre
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div className="text-sm text-gray-700 dark:text-gray-300">
                Page {page} sur {totalPages}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Précédent
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  Suivant
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Detail Panel */}
      {selectedConflict && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Détails du conflit
          </h3>

          <div className="space-y-4">
            <div>
              <ConflictBadge type={selectedConflict.conflict_type} />
              <p className="mt-3 text-gray-900 dark:text-gray-100">
                {selectedConflict.description}
              </p>
            </div>

            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Sévérité
              </p>
              <SeverityIndicator score={selectedConflict.severity_score} />
            </div>

            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Entités impliquées
              </p>
              <div className="flex flex-wrap gap-2">
                {selectedConflict.entities_involved.map((entity) => (
                  <span
                    key={entity.id}
                    className="px-3 py-1 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm text-gray-900 dark:text-gray-100"
                  >
                    {entity.name} ({entity.type})
                  </span>
                ))}
              </div>
            </div>

            {selectedConflict.status === "active" && (
              <button
                onClick={() => setShowResolutionModal(true)}
                className="w-full md:w-auto px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
              >
                Résoudre ce conflit
              </button>
            )}
          </div>
        </div>
      )}

      {/* Resolution Modal */}
      {showResolutionModal && selectedConflict && (
        <ConflictResolutionModal
          isOpen={showResolutionModal}
          onClose={() => setShowResolutionModal(false)}
          onResolve={handleResolve}
          conflictDescription={selectedConflict.description}
        />
      )}
    </div>
  );
}

export default function ConflictsPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-blue-600" /></div>}>
      <ConflictsPageContent />
    </Suspense>
  );
}
