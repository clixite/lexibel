"use client";

import { useSession } from "next-auth/react";
import { useState, useCallback } from "react";
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
  Person: "bg-accent-50 text-accent-700",
  Organization: "bg-success-50 text-success-700",
  Case: "bg-warning-50 text-warning-700",
  Document: "bg-purple-100 text-purple-700",
  Event: "bg-warning-100 text-warning-800",
  LegalConcept: "bg-pink-100 text-pink-800",
  Court: "bg-danger-50 text-danger-700",
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
        <h1 className="text-2xl font-bold text-neutral-900">Knowledge Graph</h1>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">Dossier ID</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              placeholder="UUID du dossier..."
              className="input flex-1"
            />
            <button
              onClick={loadCaseGraph}
              disabled={!caseId.trim() || loading}
              className="btn-primary px-3"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">Recherche</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Ma\u00eetre Dupont, Art. 1382..."
              className="input flex-1"
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
            <button
              onClick={handleSearch}
              disabled={!searchQuery.trim() || loading}
              className="btn-primary px-3"
            >
              <Search className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">Filtrer par type</label>
          <select
            value={filterLabel}
            onChange={(e) => setFilterLabel(e.target.value)}
            className="input"
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
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-4 text-sm">
          {error}
        </div>
      )}

      {conflicts.length > 0 && (
        <div className="bg-warning-50 border border-warning-200 px-4 py-3 rounded-md mb-4">
          <div className="flex items-center gap-2 text-warning-700 text-sm font-medium mb-1">
            <AlertTriangle className="w-4 h-4" />
            {conflicts.length} conflit(s) d&eacute;tect&eacute;(s)
          </div>
          {conflicts.map((c: any, i: number) => (
            <p key={i} className="text-sm text-warning-700 ml-6">
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
            className={`px-2.5 py-1 rounded-full text-xs font-medium ${className} cursor-pointer transition-opacity duration-150 ${
              filterLabel && filterLabel !== label ? "opacity-40" : ""
            }`}
            onClick={() => setFilterLabel(filterLabel === label ? "" : label)}
          >
            {label}
          </span>
        ))}
      </div>

      <GraphCanvas
        nodes={filteredNodes}
        edges={filteredEdges}
        onNodeClick={(node) => setSelectedNode(node)}
      />

      {/* Stats bar */}
      <div className="flex gap-4 mt-4 text-sm text-neutral-500">
        <span>{filteredNodes.length} noeuds</span>
        <span>{filteredEdges.length} relations</span>
        {caseId && (
          <button
            onClick={buildGraph}
            disabled={loading}
            className="text-accent hover:text-accent-600 font-medium transition-colors"
          >
            Reconstruire le graphe
          </button>
        )}
      </div>

      {/* Detail panel */}
      {selectedNode && (
        <div className="mt-4 bg-white rounded-lg shadow-subtle p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-neutral-900">{selectedNode.name}</h3>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${LABEL_COLORS[selectedNode.label] || "bg-neutral-100 text-neutral-600"}`}>
              {selectedNode.label}
            </span>
          </div>
          <p className="text-xs text-neutral-500">ID: {selectedNode.id}</p>
          <div className="mt-2">
            <p className="text-xs text-neutral-600">
              Connexions:{" "}
              {edges.filter((e) => e.from === selectedNode.id || e.to === selectedNode.id).length}
            </p>
          </div>
          <button
            onClick={() => setSelectedNode(null)}
            className="mt-2 text-xs text-neutral-400 hover:text-neutral-600 transition-colors"
          >
            Fermer
          </button>
        </div>
      )}
    </div>
  );
}
