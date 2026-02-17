import { Network, Users, Link, GitBranch, Activity } from "lucide-react";
import type { NetworkStats as NetworkStatsType } from "@/lib/graph/graph-utils";
import { formatNumber, formatPercentage } from "@/lib/graph/graph-utils";

export interface NetworkStatsProps {
  stats: NetworkStatsType;
  className?: string;
}

export default function NetworkStats({ stats, className = "" }: NetworkStatsProps) {
  const metrics = [
    {
      label: "Noeuds",
      value: formatNumber(stats.total_nodes),
      icon: Users,
      color: "text-blue-600 bg-blue-50",
    },
    {
      label: "Relations",
      value: formatNumber(stats.total_edges),
      icon: Link,
      color: "text-green-600 bg-green-50",
    },
    {
      label: "Densité",
      value: formatPercentage(stats.density),
      icon: Network,
      color: "text-purple-600 bg-purple-50",
    },
    {
      label: "Degré moyen",
      value: stats.avg_degree.toFixed(1),
      icon: GitBranch,
      color: "text-orange-600 bg-orange-50",
    },
    {
      label: "Degré max",
      value: stats.max_degree.toString(),
      icon: Activity,
      color: "text-red-600 bg-red-50",
    },
    {
      label: "Composantes",
      value: stats.connected_components.toString(),
      icon: Network,
      color: "text-teal-600 bg-teal-50",
    },
  ];

  return (
    <div className={`bg-white rounded-lg shadow-md border border-neutral-200 p-4 ${className}`}>
      <div className="flex items-center gap-2 mb-4">
        <Network className="w-5 h-5 text-neutral-700" />
        <h3 className="text-lg font-semibold text-neutral-900">
          Statistiques du réseau
        </h3>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {metrics.map((metric, index) => {
          const Icon = metric.icon;
          return (
            <div
              key={index}
              className="bg-neutral-50 rounded-lg p-3 border border-neutral-100"
            >
              <div className="flex items-center gap-2 mb-2">
                <div className={`p-1.5 rounded ${metric.color}`}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <p className="text-xs text-neutral-600">{metric.label}</p>
              </div>
              <p className="text-xl font-bold text-neutral-900">
                {metric.value}
              </p>
            </div>
          );
        })}
      </div>

      {/* Additional metrics */}
      {(stats.diameter > 0 || stats.avg_clustering > 0) && (
        <div className="mt-4 pt-4 border-t border-neutral-200">
          <div className="grid grid-cols-2 gap-3 text-sm">
            {stats.diameter > 0 && (
              <div>
                <p className="text-neutral-600 mb-1">Diamètre</p>
                <p className="font-semibold text-neutral-900">{stats.diameter}</p>
              </div>
            )}
            {stats.avg_clustering > 0 && (
              <div>
                <p className="text-neutral-600 mb-1">Clustering moyen</p>
                <p className="font-semibold text-neutral-900">
                  {formatPercentage(stats.avg_clustering)}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Network health indicator */}
      <div className="mt-4 pt-4 border-t border-neutral-200">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-neutral-600">
            Santé du réseau
          </span>
          <div className="flex gap-1">
            {[...Array(5)].map((_, index) => {
              const threshold = (index + 1) * 20;
              const healthScore = Math.min(
                100,
                (stats.density * 100 + stats.avg_degree * 10) / 2
              );
              return (
                <div
                  key={index}
                  className={`w-8 h-2 rounded ${
                    healthScore >= threshold
                      ? "bg-green-500"
                      : "bg-neutral-200"
                  }`}
                />
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
