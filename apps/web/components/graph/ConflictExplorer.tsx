import { AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import SeverityIndicator from "./shared/SeverityIndicator";
import type { ConflictDetection } from "@/lib/graph/graph-utils";

export interface ConflictExplorerProps {
  conflicts: ConflictDetection[];
  onConflictClick?: (conflict: ConflictDetection) => void;
  className?: string;
}

export default function ConflictExplorer({
  conflicts,
  onConflictClick,
  className = "",
}: ConflictExplorerProps) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [filterSeverity, setFilterSeverity] = useState<string>("");

  const toggleExpand = (index: number) => {
    const newExpanded = new Set(expanded);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpanded(newExpanded);
  };

  const filteredConflicts = filterSeverity
    ? conflicts.filter((c) => c.severity === filterSeverity)
    : conflicts;

  const severityCounts = {
    critical: conflicts.filter((c) => c.severity === "critical").length,
    high: conflicts.filter((c) => c.severity === "high").length,
    medium: conflicts.filter((c) => c.severity === "medium").length,
    low: conflicts.filter((c) => c.severity === "low").length,
  };

  return (
    <div className={`bg-white rounded-lg shadow-md border border-neutral-200 p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-red-600" />
          <h3 className="text-lg font-semibold text-neutral-900">
            Explorateur de conflits
          </h3>
        </div>
        <div className="text-sm text-neutral-500">
          {filteredConflicts.length} conflit{filteredConflicts.length > 1 ? "s" : ""}
        </div>
      </div>

      {/* Severity filters */}
      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => setFilterSeverity("")}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            filterSeverity === ""
              ? "bg-neutral-900 text-white"
              : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
          }`}
        >
          Tous ({conflicts.length})
        </button>
        {severityCounts.critical > 0 && (
          <button
            onClick={() => setFilterSeverity("critical")}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              filterSeverity === "critical"
                ? "bg-red-900 text-white"
                : "bg-red-100 text-red-700 hover:bg-red-200"
            }`}
          >
            Critique ({severityCounts.critical})
          </button>
        )}
        {severityCounts.high > 0 && (
          <button
            onClick={() => setFilterSeverity("high")}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              filterSeverity === "high"
                ? "bg-red-600 text-white"
                : "bg-red-50 text-red-600 hover:bg-red-100"
            }`}
          >
            Élevé ({severityCounts.high})
          </button>
        )}
        {severityCounts.medium > 0 && (
          <button
            onClick={() => setFilterSeverity("medium")}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              filterSeverity === "medium"
                ? "bg-orange-600 text-white"
                : "bg-orange-50 text-orange-600 hover:bg-orange-100"
            }`}
          >
            Moyen ({severityCounts.medium})
          </button>
        )}
        {severityCounts.low > 0 && (
          <button
            onClick={() => setFilterSeverity("low")}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              filterSeverity === "low"
                ? "bg-green-600 text-white"
                : "bg-green-50 text-green-600 hover:bg-green-100"
            }`}
          >
            Faible ({severityCounts.low})
          </button>
        )}
      </div>

      {/* Conflicts list */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {filteredConflicts.length === 0 ? (
          <div className="text-center py-8 text-neutral-500">
            Aucun conflit détecté
          </div>
        ) : (
          filteredConflicts.map((conflict, index) => (
            <div
              key={index}
              className="border border-neutral-200 rounded-lg overflow-hidden hover:border-neutral-300 transition-colors"
            >
              <button
                onClick={() => toggleExpand(index)}
                className="w-full px-4 py-3 flex items-start justify-between text-left hover:bg-neutral-50 transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-medium text-neutral-900 text-sm">
                      {conflict.entity_name}
                    </h4>
                    <span className="text-xs text-neutral-500">
                      ({conflict.entity_type})
                    </span>
                  </div>
                  <p className="text-xs text-neutral-600">
                    {conflict.conflict_type}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <SeverityIndicator
                    severity={conflict.severity}
                    size="sm"
                    showLabel={false}
                  />
                  {expanded.has(index) ? (
                    <ChevronUp className="w-4 h-4 text-neutral-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-neutral-400" />
                  )}
                </div>
              </button>

              {expanded.has(index) && (
                <div className="px-4 py-3 bg-neutral-50 border-t border-neutral-200">
                  <p className="text-sm text-neutral-700 mb-3">
                    {conflict.description}
                  </p>
                  {conflict.related_entities.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-neutral-600 mb-1">
                        Entités liées:
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {conflict.related_entities.map((entityId, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 bg-neutral-200 text-neutral-700 rounded text-xs"
                          >
                            {entityId.slice(0, 8)}...
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {onConflictClick && (
                    <button
                      onClick={() => onConflictClick(conflict)}
                      className="mt-3 text-xs text-accent hover:text-accent-600 font-medium"
                    >
                      Visualiser dans le graphe →
                    </button>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
