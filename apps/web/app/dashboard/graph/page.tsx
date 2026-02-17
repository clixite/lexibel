"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  RefreshCw,
  Loader2,
  AlertCircle,
  Filter,
  X,
} from "lucide-react";
import GraphVisualization from "@/components/graph/GraphVisualization";
import GraphControls from "@/components/graph/GraphControls";
import EntityCard from "@/components/graph/EntityCard";
import NetworkStats from "@/components/graph/NetworkStats";
import ConflictExplorer from "@/components/graph/ConflictExplorer";
import ConflictPredictionPanel from "@/components/graph/ConflictPredictionPanel";
import {
  useGraphData,
  useGraphSearch,
  useBuildGraph,
} from "@/lib/hooks/useGraphData";
import { useConflictDetection } from "@/lib/hooks/useConflictDetection";
import { useConflictPrediction } from "@/lib/hooks/useConflictPrediction";
import { useNetworkStats, useClientNetworkStats } from "@/lib/hooks/useNetworkStats";
import { transformToCytoscapeElements } from "@/lib/graph/graph-utils";
import { toast } from "sonner";

const ENTITY_TYPE_COLORS: Record<string, string> = {
  Person: "bg-blue-50 text-blue-700",
  Organization: "bg-green-50 text-green-700",
  Case: "bg-orange-50 text-orange-700",
  Document: "bg-purple-50 text-purple-700",
  Event: "bg-yellow-50 text-yellow-700",
  LegalConcept: "bg-pink-50 text-pink-700",
  Court: "bg-red-50 text-red-700",
  Location: "bg-teal-50 text-teal-700",
};

export default function GraphPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const user = session?.user as any;
  const token = user?.accessToken;
  const tenantId = user?.tenantId;

  const [caseId, setCaseId] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [filterEntityTypes, setFilterEntityTypes] = useState<string[]>([]);
  const [layout, setLayout] = useState("cola");
  const [showConflicts, setShowConflicts] = useState(false);
  const [showPredictions, setShowPredictions] = useState(false);
  const [showStats, setShowStats] = useState(true);

  // Data queries
  const graphQuery = useGraphData(caseId || undefined, token, tenantId);
  const conflictsQuery = useConflictDetection(caseId || undefined, token, tenantId);
  const predictionsQuery = useConflictPrediction(caseId || undefined, token, tenantId);
  const statsQuery = useNetworkStats(caseId || undefined, token, tenantId);

  // Mutations
  const searchMutation = useGraphSearch(token, tenantId);
  const buildMutation = useBuildGraph(token, tenantId);

  // Transform data to Cytoscape elements
  const elements = graphQuery.data
    ? transformToCytoscapeElements(
        graphQuery.data,
        conflictsQuery.data?.conflicts
      )
    : searchMutation.data?.context
    ? transformToCytoscapeElements(
        searchMutation.data.context,
        conflictsQuery.data?.conflicts
      )
    : [];

  // Client-side stats as fallback
  const clientStats = useClientNetworkStats(elements);
  const displayStats = statsQuery.data || clientStats;

  const handleLoadGraph = () => {
    if (!caseId.trim()) {
      toast.error("Veuillez entrer un ID de dossier");
      return;
    }
    graphQuery.refetch();
    conflictsQuery.refetch();
    predictionsQuery.refetch();
    statsQuery.refetch();
  };

  const handleSearch = () => {
    if (!searchQuery.trim()) {
      toast.error("Veuillez entrer une recherche");
      return;
    }
    searchMutation.mutate({
      query: searchQuery,
      case_id: caseId || undefined,
      depth: 2,
    });
  };

  const handleBuildGraph = () => {
    if (!caseId.trim()) {
      toast.error("Veuillez entrer un ID de dossier");
      return;
    }
    buildMutation.mutate({ caseId });
  };

  const handleNodeClick = (nodeData: any) => {
    setSelectedNode(nodeData);
  };

  const handleViewCase = (id: string) => {
    router.push(`/dashboard/cases/${id}`);
  };

  // Get unique entity types
  const uniqueEntityTypes = [
    ...new Set(
      elements
        .filter((el) => !el.data.source && !el.data.target)
        .map((el) => el.data.entity_type)
        .filter(Boolean)
    ),
  ];

  const toggleEntityTypeFilter = (type: string) => {
    setFilterEntityTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  // Filter elements by entity type
  const filteredElements =
    filterEntityTypes.length > 0
      ? elements.filter((el) => {
          if (el.data.source && el.data.target) {
            // Include edge if both source and target match filter
            const sourceNode = elements.find((e) => e.data.id === el.data.source);
            const targetNode = elements.find((e) => e.data.id === el.data.target);
            return (
              sourceNode &&
              targetNode &&
              filterEntityTypes.includes(sourceNode.data.entity_type) &&
              filterEntityTypes.includes(targetNode.data.entity_type)
            );
          }
          return filterEntityTypes.includes(el.data.entity_type);
        })
      : elements;

  const isLoading = graphQuery.isLoading || searchMutation.isPending || buildMutation.isPending;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 mb-1">
          Knowledge Graph
        </h1>
        <p className="text-neutral-500 text-sm">
          Visualisation et analyse du graphe de connaissances
        </p>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Dossier ID
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              placeholder="UUID du dossier..."
              className="input flex-1"
            />
            <button
              onClick={handleLoadGraph}
              disabled={!caseId.trim() || isLoading}
              className="btn-primary px-3"
              title="Charger le graphe"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Recherche sémantique
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Rechercher une entité..."
              className="input flex-1"
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
            <button
              onClick={handleSearch}
              disabled={!searchQuery.trim() || isLoading}
              className="btn-primary px-3"
              title="Rechercher"
            >
              <Search className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="flex items-end gap-2">
          <button
            onClick={handleBuildGraph}
            disabled={!caseId.trim() || isLoading}
            className="btn-secondary flex-1"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Reconstruire le graphe
          </button>
        </div>
      </div>

      {/* Error display */}
      {(graphQuery.isError || searchMutation.isError) && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <div>
              <h3 className="font-semibold text-red-900">Erreur</h3>
              <p className="text-sm text-red-700">
                {graphQuery.error?.message || searchMutation.error?.message}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Entity type filters */}
      {uniqueEntityTypes.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <Filter className="w-4 h-4 text-neutral-500" />
          <span className="text-sm font-medium text-neutral-600">Filtrer:</span>
          {uniqueEntityTypes.map((type) => (
            <button
              key={type}
              onClick={() => toggleEntityTypeFilter(type)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                filterEntityTypes.includes(type)
                  ? ENTITY_TYPE_COLORS[type] || "bg-neutral-900 text-white"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
              }`}
            >
              {type}
            </button>
          ))}
          {filterEntityTypes.length > 0 && (
            <button
              onClick={() => setFilterEntityTypes([])}
              className="px-2 py-1 text-xs text-neutral-500 hover:text-neutral-700"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      )}

      {/* Graph visualization */}
      <div className="space-y-4">
        <GraphControls
          currentLayout={layout}
          onLayoutChange={setLayout}
          className="justify-end"
        />

        <div className="relative">
          {filteredElements.length > 0 ? (
            <GraphVisualization
              elements={filteredElements}
              layout={layout}
              onNodeClick={handleNodeClick}
              onBackgroundClick={() => setSelectedNode(null)}
              height={600}
            />
          ) : (
            <div className="flex items-center justify-center h-96 bg-neutral-50 rounded-lg border border-neutral-200">
              <div className="text-center">
                <p className="text-neutral-500 mb-2">Aucun graphe chargé</p>
                <p className="text-sm text-neutral-400">
                  Entrez un ID de dossier ou effectuez une recherche
                </p>
              </div>
            </div>
          )}

          {/* Selected node card overlay */}
          {selectedNode && (
            <div className="absolute top-4 right-4 w-80">
              <EntityCard
                entity={selectedNode}
                onClose={() => setSelectedNode(null)}
                onViewCase={handleViewCase}
              />
            </div>
          )}
        </div>

        {/* Stats */}
        <div className="flex gap-4 text-sm text-neutral-500">
          <span>{filteredElements.filter((e) => !e.data.source).length} noeuds</span>
          <span>{filteredElements.filter((e) => e.data.source).length} relations</span>
          {filterEntityTypes.length > 0 && (
            <span className="text-accent">
              {filterEntityTypes.length} filtre(s) actif(s)
            </span>
          )}
        </div>
      </div>

      {/* Side panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {/* Network stats */}
        {showStats && displayStats && <NetworkStats stats={displayStats} />}

        {/* Conflicts */}
        {conflictsQuery.data && conflictsQuery.data.conflicts.length > 0 && (
          <ConflictExplorer
            conflicts={conflictsQuery.data.conflicts}
            onConflictClick={(conflict) => {
              const node = elements.find(
                (el) => el.data.id === conflict.entity_id
              );
              if (node) setSelectedNode(node.data);
            }}
          />
        )}

        {/* Predictions */}
        {predictionsQuery.data && predictionsQuery.data.predictions.length > 0 && (
          <ConflictPredictionPanel
            predictions={predictionsQuery.data.predictions}
            modelVersion={predictionsQuery.data.model_version}
            confidenceThreshold={predictionsQuery.data.confidence_threshold}
          />
        )}
      </div>
    </div>
  );
}
