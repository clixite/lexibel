"use client";

import { useSession } from "next-auth/react";
import { useState, useEffect, useCallback } from "react";
import { Share2, Search, AlertTriangle, Loader2, RefreshCw } from "lucide-react";
import { apiFetch } from "@/lib/api";
import GraphCanvas from "./GraphCanvas";

interface GraphNode {
  id: string;
  label: string;
  name: string;
}

interface GraphEdge {
  from: string;
  to: string;
  type: string;
}

const LABEL_COLORS: Record<string, string> = {
  Person: "bg-blue-100 text-blue-800",
  Organization: "bg-green-100 text-green-800",
  Case: "bg-orange-100 text-orange-800",
  Document: "bg-purple-100 text-purple-800",
  Event: "bg-yellow-100 text-yellow-800",
  LegalConcept: "bg-pink-100 text-pink-800",
  Court: "bg-red-100 text-red-800",
  Location: "bg-teal-100 text-teal-800",
};

export default function GraphPage() {
  const { data: session } = useSession();
  const [caseId, setCaseId] = useState("");
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [conflicts, setConflicts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterLabel, setFilterLabel] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const token = (session?.user as any)?.accessToken;

  const loadCaseGraph = useCallback(async () => {
    if (!token || !caseId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<any>(`/graph/case/${caseId}`, token);
      setNodes(data.nodes || []);
      setEdges(
        (data.relationships || []).map((r: any) => ({
          from: r.from_id || r.from,
          to: r.to_id || r.to,
          type: r.type,
        }))
      );

      // Also load conflicts
      const conflictData = await apiFetch<any>(`/graph/case/${caseId}/conflicts`, token);
      setConflicts(conflictData.conflicts || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token, caseId]);

  const handleSearch = async () => {
    if (!token || !searchQuery.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<any>("/graph/search", token, {
        method: "POST",
        body: JSON.stringify({
          query: searchQuery,
          case_id: caseId || undefined,
          depth: 2,
        }),
      });
      const ctx = data.context;
      setNodes(ctx.nodes || []);
      setEdges(
        (ctx.relationships || []).map((r: any) => ({
          from: r.from_id || r.from,
          to: r.to_id || r.to,
          type: r.type,
        }))
      );
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const buildGraph = async () => {
    if (!token || !caseId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await apiFetch<any>(`/graph/build/${caseId}`, token, {
        method: "POST",
        body: JSON.stringify({ documents: [] }),
      });
      await loadCaseGraph();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Filter nodes by label
  const filteredNodes = filterLabel
    ? nodes.filter((n) => n.label === filterLabel)
    : nodes;
  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));
  const filteredEdges = edges.filter(
    (e) => filteredNodeIds.has(e.from) && filteredNodeIds.has(e.to)
  );

  const uniqueLabels = [...new Set(nodes.map((n) => n.label))];

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Share2 className="w-6 h-6 text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-900">Knowledge Graph</h1>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Case selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Dossier ID</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              placeholder="UUID du dossier..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <button
              onClick={loadCaseGraph}
              disabled={!caseId.trim() || loading}
              className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Search */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Recherche</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Maître Dupont, Art. 1382..."
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
            <button
              onClick={handleSearch}
              disabled={!searchQuery.trim() || loading}
              className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              <Search className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Filtrer par type</label>
          <select
            value={filterLabel}
            onChange={(e) => setFilterLabel(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Tous les types</option>
            {uniqueLabels.map((label) => (
              <option key={label} value={label}>
                {label} ({nodes.filter((n) => n.label === label).length})
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Conflicts warning */}
      {conflicts.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 px-4 py-3 rounded-lg mb-4">
          <div className="flex items-center gap-2 text-amber-800 text-sm font-medium mb-1">
            <AlertTriangle className="w-4 h-4" />
            {conflicts.length} conflit(s) détecté(s)
          </div>
          {conflicts.map((c: any, i: number) => (
            <p key={i} className="text-sm text-amber-700 ml-6">
              {c.entity_name} ({c.entity_type}): {c.description}
            </p>
          ))}
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-2 mb-4">
        {Object.entries(LABEL_COLORS).map(([label, className]) => (
          <span
            key={label}
            className={`px-2 py-1 rounded-full text-xs font-medium ${className} cursor-pointer`}
            onClick={() => setFilterLabel(filterLabel === label ? "" : label)}
          >
            {label}
          </span>
        ))}
      </div>

      {/* Graph canvas */}
      <GraphCanvas
        nodes={filteredNodes}
        edges={filteredEdges}
        onNodeClick={(node) => setSelectedNode(node)}
      />

      {/* Stats bar */}
      <div className="flex gap-4 mt-4 text-sm text-gray-500">
        <span>{filteredNodes.length} noeuds</span>
        <span>{filteredEdges.length} relations</span>
        {caseId && (
          <button
            onClick={buildGraph}
            disabled={loading}
            className="text-blue-600 hover:text-blue-800 font-medium"
          >
            Reconstruire le graphe
          </button>
        )}
      </div>

      {/* Detail panel */}
      {selectedNode && (
        <div className="mt-4 bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-900">{selectedNode.name}</h3>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${LABEL_COLORS[selectedNode.label] || "bg-gray-100 text-gray-800"}`}>
              {selectedNode.label}
            </span>
          </div>
          <p className="text-xs text-gray-500">ID: {selectedNode.id}</p>
          <div className="mt-2">
            <p className="text-xs text-gray-600">
              Connexions:{" "}
              {edges.filter((e) => e.from === selectedNode.id || e.to === selectedNode.id).length}
            </p>
          </div>
          <button
            onClick={() => setSelectedNode(null)}
            className="mt-2 text-xs text-gray-400 hover:text-gray-600"
          >
            Fermer
          </button>
        </div>
      )}
    </div>
  );
}
