"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, Building2, User, Loader2, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { sentinelAPI, GraphNode, GraphEdge } from "@/lib/sentinel/api-client";
import SentinelGraphVisualization from "@/components/sentinel/SentinelGraphVisualization";

export default function EntityDetailPage() {
  const params = useParams();
  const entityId = params.id as string;

  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(
    null
  );
  const [depth, setDepth] = useState<1 | 2 | 3>(2);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadGraphData();
  }, [entityId, depth]);

  const loadGraphData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await sentinelAPI.getGraphData(entityId, depth);
      setGraphData({
        nodes: response.nodes,
        edges: response.edges,
      });
    } catch (err: any) {
      setError(err.message || "Erreur lors du chargement du graphe");
    } finally {
      setIsLoading(false);
    }
  };

  const centerNode = graphData?.nodes.find((n) => n.id === entityId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard/sentinel"
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
              {centerNode?.label === "Company" ? (
                <Building2 className="w-8 h-8 text-green-600 dark:text-green-400" />
              ) : (
                <User className="w-8 h-8 text-blue-600 dark:text-blue-400" />
              )}
              {centerNode?.name || "Chargement..."}
            </h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {centerNode?.label || "Entité"}
            </p>
          </div>
        </div>

        {/* Depth selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Profondeur :
          </span>
          {([1, 2, 3] as const).map((d) => (
            <button
              key={d}
              onClick={() => setDepth(d)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                depth === d
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Graph */}
      {isLoading ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      ) : error ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-red-600 dark:text-red-400 font-medium">{error}</p>
        </div>
      ) : graphData ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Graphe des relations
          </h2>
          <SentinelGraphVisualization
            nodes={graphData.nodes}
            edges={graphData.edges}
            entityId={entityId}
            height={700}
            onNodeClick={(node) => {
              console.log("Node clicked:", node);
            }}
            onExpandNode={(nodeId) => {
              window.location.href = `/dashboard/sentinel/entity/${nodeId}`;
            }}
          />
        </div>
      ) : null}

      {/* Entity Info */}
      {centerNode && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Informations
          </h2>

          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Nom</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                {centerNode.name}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Type</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                {centerNode.label}
              </dd>
            </div>

            {centerNode.properties &&
              Object.entries(centerNode.properties).map(([key, value]) => {
                if (!value) return null;
                return (
                  <div key={key}>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      {key}
                    </dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                      {String(value)}
                    </dd>
                  </div>
                );
              })}
          </dl>
        </div>
      )}

      {/* Stats */}
      {graphData && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Entités liées
            </p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
              {graphData.nodes.length - 1}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Relations
            </p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
              {graphData.edges.length}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Profondeur
            </p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
              {depth} niveau{depth > 1 ? "x" : ""}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
