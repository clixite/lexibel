"use client";

import { useState } from "react";
import { Search, Loader2, AlertTriangle } from "lucide-react";
import { sentinelAPI, ConflictCheckResponse, EntitySearchResult } from "@/lib/sentinel/api-client";
import EntitySearch from "./EntitySearch";
import ConflictCard from "./ConflictCard";
import SentinelGraphVisualization from "./SentinelGraphVisualization";

export default function ConflictCheckForm() {
  const [selectedContact, setSelectedContact] = useState<EntitySearchResult | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [result, setResult] = useState<ConflictCheckResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCheck = async () => {
    if (!selectedContact) return;

    setIsChecking(true);
    setError(null);
    setResult(null);

    try {
      const response = await sentinelAPI.checkConflict({
        contact_id: selectedContact.id,
        include_graph: true,
      });
      setResult(response);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Une erreur est survenue";
      setError(message || "Erreur lors de la vérification");
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search form */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Vérification rapide de conflits
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Contact ou Entreprise
            </label>
            <EntitySearch
              onSelect={setSelectedContact}
              placeholder="Rechercher un contact ou une entreprise..."
            />
            {selectedContact && (
              <div className="mt-2 flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <span className="font-medium">{selectedContact.name}</span>
                <span className="text-gray-400">•</span>
                <span>{selectedContact.type}</span>
                {selectedContact.conflict_count > 0 && (
                  <>
                    <span className="text-gray-400">•</span>
                    <span className="text-red-600 dark:text-red-400 font-medium">
                      {selectedContact.conflict_count} conflit{selectedContact.conflict_count > 1 ? "s" : ""} actif{selectedContact.conflict_count > 1 ? "s" : ""}
                    </span>
                  </>
                )}
              </div>
            )}
          </div>

          <div className="flex items-end">
            <button
              onClick={handleCheck}
              disabled={!selectedContact || isChecking}
              className="w-full px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isChecking ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Vérification...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  Vérifier
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-4 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg">
            <div className="flex items-center gap-2 text-red-800 dark:text-red-200">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-sm font-medium">{error}</span>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Résultat de la vérification
            </h4>

            {result.total_count === 0 ? (
              <div className="flex items-center gap-3 p-4 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800 rounded-lg">
                <div className="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center flex-shrink-0">
                  <Search className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="font-semibold text-green-900 dark:text-green-100">
                    Aucun conflit détecté
                  </p>
                  <p className="text-sm text-green-700 dark:text-green-300">
                    Le contact peut être ajouté au dossier sans problème
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900 flex items-center justify-center flex-shrink-0">
                    <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
                  </div>
                  <div>
                    <p className="font-semibold text-red-900 dark:text-red-100">
                      {result.total_count} conflit{result.total_count > 1 ? "s" : ""} détecté{result.total_count > 1 ? "s" : ""}
                    </p>
                    <p className="text-sm text-red-700 dark:text-red-300">
                      Sévérité maximale : {result.highest_severity}/100
                    </p>
                  </div>
                </div>

                {/* Conflict list */}
                <div className="grid gap-4">
                  {result.conflicts.map((conflict) => (
                    <ConflictCard key={conflict.id} conflict={conflict} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Graph visualization */}
          {result.graph_data && result.graph_data.nodes.length > 0 && (
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Graphe des relations
              </h4>
              <SentinelGraphVisualization
                nodes={result.graph_data.nodes}
                edges={result.graph_data.edges}
                height={500}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
