import { ArrowRight } from "lucide-react";
import { useCytoscapeInstance } from "./GraphVisualization";

export interface ConflictPathViewProps {
  path: string[];
  nodeNames?: Map<string, string>;
  onClose?: () => void;
  className?: string;
}

export default function ConflictPathView({
  path,
  nodeNames = new Map(),
  onClose,
  className = "",
}: ConflictPathViewProps) {
  const cy = useCytoscapeInstance();

  const handleHighlightPath = () => {
    if (!cy) return;

    // Reset
    cy.elements().removeClass("highlighted dimmed");

    // Highlight path nodes
    path.forEach((nodeId) => {
      cy.getElementById(nodeId).addClass("highlighted");
    });

    // Highlight path edges
    for (let i = 0; i < path.length - 1; i++) {
      const edge = cy
        .edges()
        .filter(
          (e) =>
            (e.data("source") === path[i] && e.data("target") === path[i + 1]) ||
            (e.data("source") === path[i + 1] && e.data("target") === path[i])
        );
      edge.addClass("highlighted");
    }

    // Dim others
    const highlighted = cy.elements(".highlighted");
    cy.elements().not(highlighted).addClass("dimmed");
  };

  const handleFocusPath = () => {
    if (!cy) return;

    const pathNodes = cy.collection();
    path.forEach((nodeId) => {
      pathNodes.merge(cy.getElementById(nodeId));
    });

    cy.fit(pathNodes, 100);
  };

  return (
    <div
      className={`bg-white rounded-lg shadow-md border border-neutral-200 p-4 ${className}`}
    >
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-neutral-900">
          Chemin de conflit
        </h4>
        {onClose && (
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 text-xs"
          >
            Fermer
          </button>
        )}
      </div>

      {/* Path visualization */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {path.map((nodeId, index) => (
          <div key={nodeId} className="flex items-center gap-2">
            <div className="bg-neutral-100 px-3 py-1.5 rounded-md">
              <p className="text-sm font-medium text-neutral-900">
                {nodeNames.get(nodeId) || nodeId.slice(0, 8)}
              </p>
              <p className="text-xs text-neutral-500">{index + 1}</p>
            </div>
            {index < path.length - 1 && (
              <ArrowRight className="w-4 h-4 text-neutral-400" />
            )}
          </div>
        ))}
      </div>

      {/* Stats */}
      <div className="flex items-center gap-4 text-xs text-neutral-600 mb-3">
        <span>
          <strong>{path.length}</strong> entités
        </span>
        <span>
          <strong>{path.length - 1}</strong> connexions
        </span>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleHighlightPath}
          className="flex-1 px-3 py-1.5 bg-accent text-white rounded-md text-sm font-medium hover:bg-accent-600 transition-colors"
        >
          Mettre en évidence
        </button>
        <button
          onClick={handleFocusPath}
          className="px-3 py-1.5 bg-neutral-100 text-neutral-700 rounded-md text-sm font-medium hover:bg-neutral-200 transition-colors"
        >
          Centrer
        </button>
      </div>
    </div>
  );
}
