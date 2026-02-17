import {
  ZoomIn,
  ZoomOut,
  Maximize,
  Download,
  Grid3x3,
  GitBranch,
  Circle,
  Network,
} from "lucide-react";
import { useCytoscapeInstance } from "./GraphVisualization";
import { layoutConfigs, exportPresets } from "@/lib/graph/cytoscape-config";
import { toast } from "sonner";

export interface GraphControlsProps {
  onLayoutChange?: (layout: string) => void;
  currentLayout?: string;
  className?: string;
}

const LAYOUTS = [
  { id: "cola", name: "Force", icon: Network },
  { id: "breadthfirst", name: "Hiérarchie", icon: GitBranch },
  { id: "circle", name: "Circulaire", icon: Circle },
  { id: "grid", name: "Grille", icon: Grid3x3 },
];

export default function GraphControls({
  onLayoutChange,
  currentLayout = "cola",
  className = "",
}: GraphControlsProps) {
  const cy = useCytoscapeInstance();

  const handleZoomIn = () => {
    if (!cy) return;
    const currentZoom = cy.zoom();
    cy.zoom({
      level: currentZoom * 1.2,
      renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
    });
  };

  const handleZoomOut = () => {
    if (!cy) return;
    const currentZoom = cy.zoom();
    cy.zoom({
      level: currentZoom / 1.2,
      renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
    });
  };

  const handleFitView = () => {
    if (!cy) return;
    cy.fit(undefined, 50);
  };

  const handleExportPNG = async () => {
    if (!cy) return;
    try {
      const blob = await cy.png(exportPresets.png);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `graph-${Date.now()}.png`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Graphe exporté en PNG");
    } catch (error) {
      toast.error("Erreur d'export");
    }
  };

  const handleLayoutChange = (layoutId: string) => {
    if (!cy) return;
    onLayoutChange?.(layoutId);
    const config = layoutConfigs[layoutId];
    if (config) {
      cy.layout(config).run();
    }
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Layout selector */}
      <div className="flex items-center gap-1 bg-white rounded-lg border border-neutral-200 p-1">
        {LAYOUTS.map((layout) => {
          const Icon = layout.icon;
          return (
            <button
              key={layout.id}
              onClick={() => handleLayoutChange(layout.id)}
              className={`p-2 rounded transition-colors ${
                currentLayout === layout.id
                  ? "bg-accent text-white"
                  : "text-neutral-600 hover:bg-neutral-100"
              }`}
              title={layout.name}
            >
              <Icon className="w-4 h-4" />
            </button>
          );
        })}
      </div>

      {/* Zoom controls */}
      <div className="flex items-center gap-1 bg-white rounded-lg border border-neutral-200 p-1">
        <button
          onClick={handleZoomIn}
          className="p-2 text-neutral-600 hover:bg-neutral-100 rounded transition-colors"
          title="Zoom avant"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-2 text-neutral-600 hover:bg-neutral-100 rounded transition-colors"
          title="Zoom arrière"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleFitView}
          className="p-2 text-neutral-600 hover:bg-neutral-100 rounded transition-colors"
          title="Ajuster à l'écran"
        >
          <Maximize className="w-4 h-4" />
        </button>
      </div>

      {/* Export */}
      <button
        onClick={handleExportPNG}
        className="px-3 py-2 bg-white rounded-lg border border-neutral-200 text-neutral-600 hover:bg-neutral-100 transition-colors flex items-center gap-2 text-sm font-medium"
      >
        <Download className="w-4 h-4" />
        Export PNG
      </button>
    </div>
  );
}
