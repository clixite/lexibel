"use client";

import { useAuth } from "@/lib/useAuth";
import { useState, useEffect } from "react";
import { Share2, Loader2, RefreshCw, Network, ChevronRight } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, Badge, Card, Button } from "@/components/ui";

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

const typeColors: Record<string, "success" | "warning" | "accent" | "danger" | "neutral"> = {
  person: "accent",
  organization: "warning",
  location: "success",
  document: "danger",
  event: "neutral",
};

export default function GraphPage() {
  const { accessToken, tenantId } = useAuth();

  const [cases, setCases] = useState<Case[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<GraphData["nodes"][0] | null>(null);
  const [loading, setLoading] = useState(false);
  const [casesLoading, setCasesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load cases on mount
  useEffect(() => {
    if (!accessToken) return;
    setCasesLoading(true);
    apiFetch<CasesResponse>("/cases", accessToken, { tenantId })
      .then((data) => setCases(data.items || []))
      .catch((err) => setError(err.message))
      .finally(() => setCasesLoading(false));
  }, [accessToken, tenantId]);

  const handleLoadGraph = async () => {
    if (!selectedCaseId.trim() || !accessToken) return;

    setLoading(true);
    setError(null);

    try {
      const data = await apiFetch<GraphData>(
        `/graph/case/${selectedCaseId}`,
        accessToken,
        { tenantId }
      );
      setGraphData(data);
      setSelectedEntity(null);
    } catch (err: any) {
      setError(err.message || "Erreur lors du chargement du graphe");
      setGraphData(null);
    } finally {
      setLoading(false);
    }
  };

  // Get entities connected to selected entity
  const getConnectedRelationships = () => {
    if (!selectedEntity || !graphData) return [];

    return graphData.edges.filter(
      (edge) => edge.source === selectedEntity.id || edge.target === selectedEntity.id
    );
  };

  const getConnectedNodes = () => {
    if (!selectedEntity || !graphData) return [];

    const connectedIds = new Set<string>();
    graphData.edges.forEach((edge) => {
      if (edge.source === selectedEntity.id) connectedIds.add(edge.target);
      if (edge.target === selectedEntity.id) connectedIds.add(edge.source);
    });

    return graphData.nodes.filter((node) => connectedIds.has(node.id));
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center py-8 md:py-12">
        <h1 className="text-4xl md:text-5xl font-bold text-neutral-900 mb-2">
          Knowledge Graph
        </h1>
        <p className="text-neutral-500 text-lg">
          Visualisez les relations entre entités de votre dossier
        </p>
      </div>

      {/* Case Selector */}
      <Card className="max-w-2xl mx-auto w-full">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Sélectionner un dossier
            </label>
            <select
              value={selectedCaseId}
              onChange={(e) => setSelectedCaseId(e.target.value)}
              className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-200 disabled:opacity-50"
              disabled={casesLoading || loading}
            >
              <option value="">Choisir un dossier...</option>
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          </div>
          <Button
            onClick={handleLoadGraph}
            disabled={loading || !selectedCaseId.trim()}
            loading={loading}
            className="w-full"
            icon={<RefreshCw className="w-4 h-4" />}
          >
            Charger le graphe
          </Button>
        </div>
      </Card>

      {/* Error State */}
      {error && <ErrorState message={error} onRetry={() => setError(null)} />}

      {/* Loading State */}
      {loading && <LoadingSkeleton variant="card" />}

      {/* Graph Section */}
      {!loading && graphData ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-6xl mx-auto w-full">
          {/* Main Visualization */}
          <div className="lg:col-span-2">
            <Card>
              <div className="space-y-4">
                {/* Placeholder Visualization */}
                <div className="bg-gradient-to-br from-accent-50 to-accent-100 rounded-lg border-2 border-dashed border-accent-300 h-96 flex items-center justify-center">
                  <div className="text-center">
                    <Network className="w-16 h-16 text-accent-300 mx-auto mb-4" />
                    <p className="text-neutral-600 font-medium text-lg">
                      Visualisation du Graphe
                    </p>
                    <p className="text-sm text-neutral-500 mt-2">
                      Graphe interactif en préparation - {graphData.nodes.length} entités, {graphData.edges.length} relations
                    </p>
                  </div>
                </div>

                {/* Graph Stats */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-neutral-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-accent">{graphData.nodes.length}</p>
                    <p className="text-xs text-neutral-600 mt-1">Entités</p>
                  </div>
                  <div className="bg-neutral-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-accent">{graphData.edges.length}</p>
                    <p className="text-xs text-neutral-600 mt-1">Relations</p>
                  </div>
                  <div className="bg-neutral-50 rounded-lg p-3 text-center">
                    <p className="text-2xl font-bold text-accent">{new Set(graphData.nodes.map((n) => n.type)).size}</p>
                    <p className="text-xs text-neutral-600 mt-1">Types</p>
                  </div>
                </div>

                {/* Entities List */}
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold text-neutral-700">Entités</h3>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {graphData.nodes.map((node) => (
                      <button
                        key={node.id}
                        onClick={() => setSelectedEntity(node)}
                        className={`w-full text-left px-3 py-2 rounded-lg transition-all ${
                          selectedEntity?.id === node.id
                            ? "bg-accent text-white"
                            : "bg-neutral-50 hover:bg-neutral-100 text-neutral-900"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <p className="font-medium truncate">{node.label}</p>
                            <div className="mt-1">
                              <Badge
                                variant={typeColors[node.type] || "neutral"}
                                size="sm"
                              >
                                {node.type}
                              </Badge>
                            </div>
                          </div>
                          <ChevronRight className="w-4 h-4 flex-shrink-0 ml-2" />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          </div>

          {/* Side Panel - Entity Details */}
          <div className="lg:col-span-1">
            {selectedEntity ? (
              <Card>
                <div className="space-y-6">
                  {/* Entity Header */}
                  <div className="space-y-3">
                    <h2 className="text-lg font-bold text-neutral-900">{selectedEntity.label}</h2>
                    <Badge variant={typeColors[selectedEntity.type] || "neutral"}>
                      {selectedEntity.type}
                    </Badge>
                  </div>

                  {/* Properties */}
                  {selectedEntity.properties && Object.keys(selectedEntity.properties).length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-neutral-700 uppercase tracking-wider mb-3">
                        Propriétés
                      </p>
                      <div className="space-y-2">
                        {Object.entries(selectedEntity.properties).map(([key, value]) => (
                          <div key={key} className="text-sm">
                            <p className="text-neutral-500 text-xs uppercase tracking-wide mb-1">{key}</p>
                            <p className="font-medium text-neutral-900 bg-neutral-50 rounded px-2 py-1">
                              {value}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Related Entities */}
                  {getConnectedNodes().length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-neutral-700 uppercase tracking-wider mb-3">
                        Entités Connectées ({getConnectedNodes().length})
                      </p>
                      <div className="space-y-2">
                        {getConnectedNodes().map((node) => (
                          <button
                            key={node.id}
                            onClick={() => setSelectedEntity(node)}
                            className="w-full text-left px-2 py-2 rounded border border-neutral-200 hover:bg-neutral-50 transition-colors"
                          >
                            <p className="font-medium text-sm text-neutral-900">{node.label}</p>
                            <div className="mt-1">
                              <Badge variant={typeColors[node.type] || "neutral"} size="sm">
                                {node.type}
                              </Badge>
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Relationships */}
                  {getConnectedRelationships().length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-neutral-700 uppercase tracking-wider mb-3">
                        Relations ({getConnectedRelationships().length})
                      </p>
                      <div className="space-y-2">
                        {getConnectedRelationships().map((edge, idx) => (
                          <div key={idx} className="text-xs bg-neutral-50 rounded p-2">
                            <p className="text-neutral-600">
                              <span className="font-semibold">{edge.relationship}</span>
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            ) : (
              <Card>
                <div className="text-center py-8">
                  <Share2 className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
                  <p className="text-sm text-neutral-600">
                    Cliquez sur une entité pour voir ses détails
                  </p>
                </div>
              </Card>
            )}
          </div>
        </div>
      ) : !loading && !error && !graphData ? (
        <Card className="max-w-2xl mx-auto w-full text-center py-12">
          <Network className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-neutral-900 mb-2">
            Aucun graphe chargé
          </h3>
          <p className="text-neutral-500">
            Sélectionnez un dossier et cliquez sur "Charger le graphe" pour visualiser les relations
          </p>
        </Card>
      ) : null}
    </div>
  );
}
