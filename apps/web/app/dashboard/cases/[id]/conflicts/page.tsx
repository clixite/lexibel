"use client";

import { useAuth } from "@/lib/useAuth";
import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  ArrowLeft,
  AlertTriangle,
  TrendingUp,
  Loader2,
  AlertCircle,
  Eye,
} from "lucide-react";
import GraphVisualization from "@/components/graph/GraphVisualization";
import GraphControls from "@/components/graph/GraphControls";
import EntityCard from "@/components/graph/EntityCard";
import ConflictExplorer from "@/components/graph/ConflictExplorer";
import ConflictPredictionPanel from "@/components/graph/ConflictPredictionPanel";
import ConflictPathView from "@/components/graph/ConflictPathView";
import RiskScoreGauge from "@/components/graph/shared/RiskScoreGauge";
import { useGraphData } from "@/lib/hooks/useGraphData";
import { useConflictDetection } from "@/lib/hooks/useConflictDetection";
import { useConflictPrediction } from "@/lib/hooks/useConflictPrediction";
import {
  transformToCytoscapeElements,
  calculateRiskScore,
  findShortestPath,
} from "@/lib/graph/graph-utils";
import type { ConflictDetection } from "@/lib/graph/graph-utils";

export default function CaseConflictsPage({
  params,
}: {
  params: { id: string };
}) {
  const { accessToken, tenantId } = useAuth();
  const router = useRouter();
  const token = accessToken;

  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [selectedConflict, setSelectedConflict] = useState<ConflictDetection | null>(null);
  const [conflictPath, setConflictPath] = useState<string[] | null>(null);
  const [layout, setLayout] = useState("cola");
  const [viewMode, setViewMode] = useState<"all" | "conflicts">("conflicts");

  // Queries
  const graphQuery = useGraphData(params.id, token, tenantId);
  const conflictsQuery = useConflictDetection(params.id, token, tenantId);
  const predictionsQuery = useConflictPrediction(params.id, token, tenantId);

  // Transform data
  const allElements = graphQuery.data
    ? transformToCytoscapeElements(graphQuery.data, conflictsQuery.data?.conflicts)
    : [];

  // Filter to show only conflict-related nodes
  const conflictElements =
    viewMode === "conflicts" && conflictsQuery.data
      ? allElements.filter((el) => {
          if (el.data.source || el.data.target) {
            // Include edges connected to conflict nodes
            const sourceHasConflict = allElements.find(
              (e) =>
                e.data.id === el.data.source && e.data.has_conflicts === "true"
            );
            const targetHasConflict = allElements.find(
              (e) =>
                e.data.id === el.data.target && e.data.has_conflicts === "true"
            );
            return sourceHasConflict || targetHasConflict;
          }
          return el.data.has_conflicts === "true";
        })
      : allElements;

  const displayElements = viewMode === "conflicts" ? conflictElements : allElements;

  // Calculate overall risk score
  const overallRiskScore = conflictsQuery.data
    ? calculateRiskScore(conflictsQuery.data.conflicts)
    : 0;

  // Create node name map
  const nodeNamesMap = new Map(
    allElements
      .filter((el) => !el.data.source && !el.data.target && el.data.id && el.data.name)
      .map((el) => [el.data.id as string, el.data.name as string])
  );

  const handleConflictClick = (conflict: ConflictDetection) => {
    setSelectedConflict(conflict);

    // Find node
    const node = allElements.find((el) => el.data.id === conflict.entity_id);
    if (node) {
      setSelectedNode(node.data);

      // If there are related entities, find path
      if (conflict.related_entities.length > 0) {
        const path = findShortestPath(
          allElements,
          conflict.entity_id,
          conflict.related_entities[0]
        );
        if (path.length > 0) {
          setConflictPath(path);
        }
      }
    }
  };

  const handleNodeClick = (nodeData: any) => {
    setSelectedNode(nodeData);
    setConflictPath(null);
  };

  if (graphQuery.isLoading || conflictsQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (graphQuery.isError || conflictsQuery.isError) {
    return (
      <div>
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-neutral-600 hover:text-neutral-900 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour
        </button>
        <div className="bg-red-50 rounded-lg p-6 border border-red-200">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-6 w-6 text-red-600" />
            <div>
              <h3 className="font-semibold text-red-900">Erreur de chargement</h3>
              <p className="text-sm text-red-700 mt-1">
                Impossible de charger les données de conflit.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const conflicts = conflictsQuery.data?.conflicts || [];
  const predictions = predictionsQuery.data?.predictions || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-neutral-600 hover:text-neutral-900 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour au dossier
        </button>
        <h1 className="text-2xl font-bold text-neutral-900 mb-1">
          Analyse des conflits
        </h1>
        <p className="text-neutral-500 text-sm">
          Détection et prédiction de conflits d'intérêts
        </p>
      </div>

      {/* Risk summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card bg-gradient-to-br from-red-50 to-orange-50 border-red-200">
          <div className="flex items-center justify-between mb-2">
            <AlertTriangle className="w-8 h-8 text-red-600" />
            <span className="text-3xl font-bold text-red-700">
              {conflicts.length}
            </span>
          </div>
          <p className="text-sm font-medium text-red-800">
            Conflits détectés
          </p>
        </div>

        <div className="card bg-gradient-to-br from-accent-50 to-accent-50 border-accent-200">
          <div className="flex items-center justify-between mb-2">
            <TrendingUp className="w-8 h-8 text-accent-600" />
            <span className="text-3xl font-bold text-accent-700">
              {predictions.length}
            </span>
          </div>
          <p className="text-sm font-medium text-accent-800">
            Prédictions IA
          </p>
        </div>

        <div className="card bg-gradient-to-br from-orange-50 to-yellow-50 border-orange-200">
          <div className="flex items-center justify-between mb-2">
            <AlertCircle className="w-8 h-8 text-orange-600" />
            <span className="text-3xl font-bold text-orange-700">
              {conflicts.filter((c) => c.severity === "high" || c.severity === "critical").length}
            </span>
          </div>
          <p className="text-sm font-medium text-orange-800">
            Risques élevés
          </p>
        </div>

        <div className="card flex items-center justify-center">
          <RiskScoreGauge score={overallRiskScore} size="md" showLabel={false} />
        </div>
      </div>

      {/* View mode toggle */}
      <div className="flex items-center gap-2">
        <Eye className="w-4 h-4 text-neutral-500" />
        <span className="text-sm font-medium text-neutral-600">Vue:</span>
        <div className="flex gap-1 bg-neutral-100 rounded-lg p-1">
          <button
            onClick={() => setViewMode("conflicts")}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              viewMode === "conflicts"
                ? "bg-white text-neutral-900 shadow-sm"
                : "text-neutral-600 hover:text-neutral-900"
            }`}
          >
            Conflits uniquement
          </button>
          <button
            onClick={() => setViewMode("all")}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              viewMode === "all"
                ? "bg-white text-neutral-900 shadow-sm"
                : "text-neutral-600 hover:text-neutral-900"
            }`}
          >
            Graphe complet
          </button>
        </div>
      </div>

      {/* Graph */}
      <div className="space-y-4">
        <GraphControls
          currentLayout={layout}
          onLayoutChange={setLayout}
          className="justify-end"
        />

        <div className="relative">
          {displayElements.length > 0 ? (
            <GraphVisualization
              elements={displayElements}
              layout={layout}
              onNodeClick={handleNodeClick}
              onBackgroundClick={() => {
                setSelectedNode(null);
                setConflictPath(null);
              }}
              height={600}
            />
          ) : (
            <div className="flex items-center justify-center h-96 bg-neutral-50 rounded-lg border border-neutral-200">
              <div className="text-center">
                <AlertTriangle className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
                <p className="text-neutral-500 mb-1">Aucun conflit détecté</p>
                <p className="text-sm text-neutral-400">
                  Ce dossier ne présente aucun conflit d'intérêts
                </p>
              </div>
            </div>
          )}

          {/* Entity card overlay */}
          {selectedNode && (
            <div className="absolute top-4 right-4 w-80">
              <EntityCard
                entity={selectedNode}
                onClose={() => setSelectedNode(null)}
                onViewCase={(id) => router.push(`/dashboard/cases/${id}`)}
              />
            </div>
          )}

          {/* Conflict path overlay */}
          {conflictPath && conflictPath.length > 0 && (
            <div className="absolute bottom-4 left-4 w-96">
              <ConflictPathView
                path={conflictPath}
                nodeNames={nodeNamesMap}
                onClose={() => setConflictPath(null)}
              />
            </div>
          )}
        </div>
      </div>

      {/* Analysis panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Detected conflicts */}
        {conflicts.length > 0 && (
          <ConflictExplorer
            conflicts={conflicts}
            onConflictClick={handleConflictClick}
          />
        )}

        {/* Predictions */}
        {predictions.length > 0 && predictionsQuery.data && (
          <ConflictPredictionPanel
            predictions={predictions}
            modelVersion={predictionsQuery.data.model_version}
            confidenceThreshold={predictionsQuery.data.confidence_threshold}
          />
        )}
      </div>

      {/* No conflicts message */}
      {conflicts.length === 0 && predictions.length === 0 && (
        <div className="card bg-green-50 border-green-200 text-center py-12">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-4">
            <AlertTriangle className="w-8 h-8 text-green-600" />
          </div>
          <h3 className="text-lg font-semibold text-green-900 mb-2">
            Aucun conflit détecté
          </h3>
          <p className="text-green-700 max-w-md mx-auto">
            L'analyse du graphe de connaissances n'a révélé aucun conflit
            d'intérêts potentiel pour ce dossier.
          </p>
        </div>
      )}
    </div>
  );
}
