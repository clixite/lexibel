import { X, ExternalLink, AlertTriangle } from "lucide-react";
import { useCytoscapeInstance } from "./GraphVisualization";
import ConflictBadge from "./shared/ConflictBadge";
import type { ConflictDetection } from "@/lib/graph/graph-utils";

export interface EntityCardProps {
  entity: {
    id: string;
    name: string;
    entity_type: string;
    has_conflicts?: string;
    conflict_count?: number;
    conflicts?: ConflictDetection[];
    [key: string]: any;
  };
  onClose: () => void;
  onViewCase?: (caseId: string) => void;
  className?: string;
}

const ENTITY_TYPE_LABELS: Record<string, string> = {
  Person: "Personne",
  Organization: "Organisation",
  Case: "Dossier",
  Document: "Document",
  Event: "Événement",
  LegalConcept: "Concept Juridique",
  Court: "Tribunal",
  Location: "Localisation",
};

const ENTITY_TYPE_COLORS: Record<string, string> = {
  Person: "bg-blue-100 text-blue-700",
  Organization: "bg-green-100 text-green-700",
  Case: "bg-orange-100 text-orange-700",
  Document: "bg-purple-100 text-purple-700",
  Event: "bg-yellow-100 text-yellow-700",
  LegalConcept: "bg-pink-100 text-pink-700",
  Court: "bg-red-100 text-red-700",
  Location: "bg-teal-100 text-teal-700",
};

export default function EntityCard({
  entity,
  onClose,
  onViewCase,
  className = "",
}: EntityCardProps) {
  const cy = useCytoscapeInstance();

  const handleHighlightNeighbors = () => {
    if (!cy) return;

    // Reset all styles
    cy.elements().removeClass("highlighted dimmed");

    // Get neighbors
    const node = cy.getElementById(entity.id);
    const neighbors = node.neighborhood();

    // Highlight node and neighbors
    node.addClass("highlighted");
    neighbors.addClass("highlighted");

    // Dim others
    cy.elements().not(node).not(neighbors).addClass("dimmed");
  };

  const handleResetHighlight = () => {
    if (!cy) return;
    cy.elements().removeClass("highlighted dimmed");
  };

  const typeLabel =
    ENTITY_TYPE_LABELS[entity.entity_type] || entity.entity_type;
  const typeColor =
    ENTITY_TYPE_COLORS[entity.entity_type] || "bg-neutral-100 text-neutral-700";

  const hasConflicts = entity.has_conflicts === "true";
  const conflictCount = entity.conflict_count || 0;

  return (
    <div
      className={`bg-white rounded-lg shadow-lg border border-neutral-200 p-4 ${className}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-lg font-semibold text-neutral-900">
              {entity.name}
            </h3>
            {hasConflicts && <ConflictBadge count={conflictCount} size="sm" />}
          </div>
          <span className={`px-2 py-1 rounded text-xs font-medium ${typeColor}`}>
            {typeLabel}
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-neutral-400 hover:text-neutral-600 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Properties */}
      <div className="space-y-2 mb-4">
        <div className="text-xs text-neutral-500">
          <span className="font-medium">ID:</span>{" "}
          <code className="bg-neutral-100 px-1 py-0.5 rounded">
            {entity.id.slice(0, 16)}...
          </code>
        </div>
        {Object.entries(entity)
          .filter(
            ([key]) =>
              ![
                "id",
                "name",
                "entity_type",
                "label",
                "has_conflicts",
                "conflict_count",
                "conflicts",
              ].includes(key)
          )
          .slice(0, 5)
          .map(([key, value]) => (
            <div key={key} className="text-sm">
              <span className="font-medium text-neutral-700">
                {key.replace(/_/g, " ")}:
              </span>{" "}
              <span className="text-neutral-600">
                {typeof value === "object"
                  ? JSON.stringify(value)
                  : String(value)}
              </span>
            </div>
          ))}
      </div>

      {/* Conflicts */}
      {hasConflicts && entity.conflicts && entity.conflicts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          <div className="flex items-center gap-2 text-red-700 font-medium mb-2 text-sm">
            <AlertTriangle className="w-4 h-4" />
            Conflits détectés ({conflictCount})
          </div>
          <div className="space-y-2">
            {entity.conflicts.slice(0, 3).map((conflict, index) => (
              <div
                key={index}
                className="text-xs bg-white rounded p-2 border border-red-100"
              >
                <p className="font-medium text-red-800">
                  {conflict.conflict_type}
                </p>
                <p className="text-red-600 mt-1">{conflict.description}</p>
              </div>
            ))}
            {conflictCount > 3 && (
              <p className="text-xs text-red-600 text-center">
                +{conflictCount - 3} autre(s) conflit(s)
              </p>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleHighlightNeighbors}
          className="flex-1 px-3 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent-600 transition-colors"
        >
          Afficher les connexions
        </button>
        <button
          onClick={handleResetHighlight}
          className="px-3 py-2 bg-neutral-100 text-neutral-700 rounded-lg text-sm font-medium hover:bg-neutral-200 transition-colors"
        >
          Réinitialiser
        </button>
      </div>

      {entity.entity_type === "Case" && entity.id && onViewCase && (
        <button
          onClick={() => onViewCase(entity.id)}
          className="w-full mt-2 px-3 py-2 border border-neutral-200 text-neutral-700 rounded-lg text-sm font-medium hover:bg-neutral-50 transition-colors flex items-center justify-center gap-2"
        >
          <ExternalLink className="w-4 h-4" />
          Voir le dossier
        </button>
      )}
    </div>
  );
}
