"use client";

import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";
import { Share2, Loader2, RefreshCw } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, Badge } from "@/components/ui";

interface Case {
  id: string;
  title: string;
}

interface CasesResponse {
  items: Case[];
}

interface GraphData {
  nodes: Array<{
    id: string;
    label: string;
    type: string;
    properties?: Record<string, string>;
  }>;
  edges: Array<{
    source: string;
    target: string;
    relationship: string;
  }>;
}

export default function GraphPage() {
  const { data: session } = useSession();
  const user = session?.user as any;
  const token = user?.accessToken;
  const tenantId = user?.tenantId;

  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<GraphData["nodes"][0] | null>(null);
  const [loading, setLoading] = useState(false);
  const [casesLoading, setCasesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load cases on mount
  useEffect(() => {
    if (!token) return;
    setCasesLoading(true);
    apiFetch<CasesResponse>("/cases", token, { tenantId })
      .then((data) => setCases(data.items || []))
      .catch((err) => setError(err.message))
      .finally(() => setCasesLoading(false));
  }, [token, tenantId]);

  const handleLoadGraph = async () => {
    if (!selectedCaseId.trim() || !token) return;

    setLoading(true);
    setError(null);

    try {
      const data = await apiFetch<GraphData>(
        `/graph/case/${selectedCaseId}`,
        token,
        { tenantId }
      );
      setGraphData(data);
    } catch (err: any) {
      setError(err.message || "Erreur lors du chargement du graphe");
      setGraphData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-accent-50 flex items-center justify-center">
          <Share2 className="w-5 h-5 text-accent" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">
            Knowledge Graph
          </h1>
          <p className="text-neutral-500 text-sm">
            Visualisation des relations entre entités
          </p>
        </div>
      </div>

      {/* Case Selector */}
      <div className="bg-white rounded-lg shadow-subtle p-4 space-y-3">
        <label className="block text-sm font-medium text-neutral-700">
          Sélectionner un dossier
        </label>
        <div className="flex gap-2">
          <select
            value={selectedCaseId}
            onChange={(e) => setSelectedCaseId(e.target.value)}
            className="input flex-1"
            disabled={casesLoading || loading}
          >
            <option value="">Choisir un dossier...</option>
            {cases.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>
          <button
            onClick={handleLoadGraph}
            disabled={loading || !selectedCaseId.trim()}
            className="btn-primary px-4 flex items-center gap-2"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Charger
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && <ErrorState message={error} onRetry={() => setError(null)} />}

      {/* Graph Visualization Area */}
      {loading && <LoadingSkeleton variant="card" />}

      {!loading && graphData ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Visualization */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-subtle p-4">
              <div className="bg-neutral-50 rounded border-2 border-dashed border-neutral-300 h-96 flex items-center justify-center">
                <div className="text-center">
                  <Share2 className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
                  <p className="text-neutral-600 font-medium">
                    Graphe disponible bientôt
                  </p>
                  <p className="text-sm text-neutral-500 mt-1">
                    Visualisation interactive en préparation
                  </p>
                </div>
              </div>
              <div className="mt-3 text-sm text-neutral-600">
                <p>
                  <span className="font-semibold">{graphData.nodes.length}</span> entités
                  {" "}
                  <span className="font-semibold">{graphData.edges.length}</span> relations
                </p>
              </div>
            </div>
          </div>

          {/* Side Panel - Entity Details */}
          <div className="bg-white rounded-lg shadow-subtle p-4">
            <h3 className="font-semibold text-neutral-900 mb-4">
              Détails de l'entité
            </h3>

            {selectedEntity ? (
              <div className="space-y-4">
                <div>
                  <p className="text-xs text-neutral-500 uppercase tracking-wider">Nom</p>
                  <p className="font-semibold text-neutral-900">{selectedEntity.label}</p>
                </div>

                <div>
                  <p className="text-xs text-neutral-500 uppercase tracking-wider">Type</p>
                  <Badge variant="accent" size="sm">
                    {selectedEntity.type}
                  </Badge>
                </div>

                {selectedEntity.properties && Object.keys(selectedEntity.properties).length > 0 && (
                  <div>
                    <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">
                      Propriétés
                    </p>
                    <div className="space-y-2">
                      {Object.entries(selectedEntity.properties).map(([key, value]) => (
                        <div key={key} className="text-sm">
                          <span className="text-neutral-600">{key}:</span>
                          <span className="font-medium text-neutral-900 ml-2">{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-neutral-500">
                Cliquez sur une entité pour voir ses détails
              </p>
            )}
          </div>
        </div>
      ) : !loading && !error && !graphData ? (
        <div className="bg-white rounded-lg shadow-subtle p-12 text-center">
          <Share2 className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-neutral-900 mb-2">
            Aucun graphe chargé
          </h3>
          <p className="text-neutral-500">
            Sélectionnez un dossier et cliquez sur "Charger" pour visualiser son graphe
          </p>
        </div>
      ) : null}
    </div>
  );
}
