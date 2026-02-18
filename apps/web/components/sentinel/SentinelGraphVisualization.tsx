"use client";

import { useEffect, useRef, useState } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import cola from "cytoscape-cola";
import { GraphNode, GraphEdge } from "@/lib/sentinel/api-client";
import {
  ZoomIn,
  ZoomOut,
  Maximize,
  Download,
  RefreshCw,
  Tag,
  Play,
  Pause,
} from "lucide-react";

if (typeof cytoscape !== "undefined") {
  cytoscape.use(cola);
}

// SENTINEL-specific styles
const sentinelStylesheet: any[] = [
  {
    selector: "node",
    style: {
      backgroundColor: (ele: any) => {
        const label = ele.data("label");
        if (label === "Person") return "#3b82f6"; // blue
        if (label === "Company") return "#22c55e"; // green
        if (label === "Case") return "#f97316"; // orange
        if (label === "Lawyer") return "#a855f7"; // purple
        return "#6b7280"; // gray
      },
      shape: (ele: any) => {
        const label = ele.data("label");
        if (label === "Person") return "ellipse";
        if (label === "Company") return "rectangle";
        if (label === "Case") return "diamond";
        if (label === "Lawyer") return "hexagon";
        return "ellipse";
      },
      label: "data(name)",
      "text-valign": "center",
      "text-halign": "center",
      "font-size": "11px",
      "font-weight": "600",
      color: "#ffffff",
      "text-outline-color": (ele: any) => {
        const label = ele.data("label");
        if (label === "Person") return "#3b82f6";
        if (label === "Company") return "#22c55e";
        if (label === "Case") return "#f97316";
        if (label === "Lawyer") return "#a855f7";
        return "#6b7280";
      },
      "text-outline-width": 2,
      width: 50,
      height: 50,
      "border-width": 3,
      "border-color": "#ffffff",
    },
  },
  {
    selector: "node:selected",
    style: {
      "border-color": "#fbbf24",
      "border-width": 5,
    },
  },
  {
    selector: "node.conflict",
    style: {
      "border-color": "#ef4444",
      "border-width": 5,
      "border-style": "double",
    },
  },
  {
    selector: "node.highlighted",
    style: {
      "border-color": "#fbbf24",
      "border-width": 4,
    },
  },
  {
    selector: "edge",
    style: {
      width: 2,
      "line-color": (ele: any) => {
        const type = ele.data("type");
        if (type === "REPRESENTS") return "#3b82f6";
        if (type === "OPPOSES") return "#ef4444";
        if (type === "RELATED_TO") return "#6b7280";
        if (type === "SHAREHOLDER") return "#22c55e";
        if (type === "DIRECTOR") return "#a855f7";
        if (type === "OWNS") return "#22c55e";
        if (type === "SUBSIDIARY_OF") return "#22c55e";
        if (type === "PARTNER") return "#eab308";
        if (type === "FAMILY") return "#ec4899";
        if (type === "ADVISED_BY") return "#14b8a6";
        return "#94a3b8";
      },
      "target-arrow-color": (ele: any) => {
        const type = ele.data("type");
        if (type === "REPRESENTS") return "#3b82f6";
        if (type === "OPPOSES") return "#ef4444";
        if (type === "RELATED_TO") return "#6b7280";
        if (type === "SHAREHOLDER") return "#22c55e";
        if (type === "DIRECTOR") return "#a855f7";
        if (type === "OWNS") return "#22c55e";
        if (type === "SUBSIDIARY_OF") return "#22c55e";
        if (type === "PARTNER") return "#eab308";
        if (type === "FAMILY") return "#ec4899";
        if (type === "ADVISED_BY") return "#14b8a6";
        return "#94a3b8";
      },
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      label: "data(type)",
      "font-size": "9px",
      color: "#475569",
      "text-background-color": "#ffffff",
      "text-background-opacity": 0.9,
      "text-background-padding": 2,
      "text-background-shape": "roundrectangle",
      "text-rotation": "autorotate",
      "line-style": (ele: any) => {
        return ele.data("type") === "OPPOSES" ? "dashed" : "solid";
      },
    },
  },
  {
    selector: "edge.conflict-path",
    style: {
      width: 4,
      "line-color": "#ef4444",
    },
  },
  {
    selector: "edge.highlighted",
    style: {
      width: 3,
    },
  },
];

interface SentinelGraphVisualizationProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  entityId?: string;
  highlightConflict?: {
    nodeIds: string[];
    edgeIds: string[];
  };
  onNodeClick?: (node: GraphNode) => void;
  onExpandNode?: (nodeId: string) => void;
  className?: string;
  height?: number;
}

export default function SentinelGraphVisualization({
  nodes,
  edges,
  entityId,
  highlightConflict,
  onNodeClick,
  onExpandNode,
  className = "",
  height = 600,
}: SentinelGraphVisualizationProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [showLabels, setShowLabels] = useState(true);
  const [physicsEnabled, setPhysicsEnabled] = useState(true);

  // Initialize Cytoscape
  useEffect(() => {
    if (!containerRef.current || cyRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: [],
      style: sentinelStylesheet,
      minZoom: 0.2,
      maxZoom: 4,
      wheelSensitivity: 0.2,
    });

    cyRef.current = cy;
    setIsReady(true);

    // Node click
    cy.on("tap", "node", (event) => {
      const node = event.target;
      const nodeData: GraphNode = {
        id: node.data("id"),
        label: node.data("label"),
        name: node.data("name"),
        properties: node.data("properties"),
      };
      onNodeClick?.(nodeData);

      // Highlight connected nodes
      cy.elements().removeClass("highlighted");
      node.addClass("highlighted");
      node.connectedEdges().addClass("highlighted");
      node.neighborhood("node").addClass("highlighted");
    });

    // Node double-click to expand
    cy.on("dbltap", "node", (event) => {
      const nodeId = event.target.data("id");
      onExpandNode?.(nodeId);
    });

    // Background click
    cy.on("tap", (event) => {
      if (event.target === cy) {
        cy.elements().removeClass("highlighted");
      }
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
      setIsReady(false);
    };
  }, [onNodeClick, onExpandNode]);

  // Update elements
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !isReady) return;

    // Convert to Cytoscape format
    const elements: ElementDefinition[] = [
      ...nodes.map((node) => ({
        data: {
          id: node.id,
          label: node.label,
          name: node.name,
          properties: node.properties,
        },
      })),
      ...edges.map((edge, idx) => ({
        data: {
          id: `edge-${idx}`,
          source: edge.from,
          target: edge.to,
          type: edge.type,
          properties: edge.properties,
        },
      })),
    ];

    cy.elements().remove();
    cy.add(elements);

    // Apply conflict highlighting
    if (highlightConflict) {
      highlightConflict.nodeIds.forEach((nodeId) => {
        cy.getElementById(nodeId).addClass("conflict");
      });
      // Note: edge highlighting would need edge IDs from backend
    }

    // Run layout
    if (physicsEnabled) {
      cy.layout({
        name: "cola",
        animate: true,
        animationDuration: 1000,
        nodeSpacing: 80,
        edgeLength: 150,
        fit: true,
        padding: 50,
        randomize: false,
        avoidOverlap: true,
      } as any).run();
    } else {
      cy.fit(undefined, 50);
    }
  }, [nodes, edges, highlightConflict, isReady, physicsEnabled]);

  // Toggle labels
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !isReady) return;

    if (showLabels) {
      cy.style().selector("node").style("label", "data(name)").update();
      cy.style().selector("edge").style("label", "data(type)").update();
    } else {
      cy.style().selector("node").style("label", "").update();
      cy.style().selector("edge").style("label", "").update();
    }
  }, [showLabels, isReady]);

  // Toolbar actions
  const zoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.2);
  const zoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const resetView = () => cyRef.current?.fit(undefined, 50);
  const exportPNG = () => {
    const png = cyRef.current?.png({ output: "blob", bg: "#ffffff", full: true, scale: 2 });
    if (png) {
      const url = URL.createObjectURL(png as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sentinel-graph-${Date.now()}.png`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className={`relative ${className}`}>
      {/* Graph container */}
      <div
        ref={containerRef}
        className="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700"
        style={{ height: `${height}px` }}
      />

      {/* Toolbar */}
      <div className="absolute top-4 right-4 flex flex-col gap-2">
        <button
          onClick={zoomIn}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-600"
          title="Zoom avant"
        >
          <ZoomIn className="w-4 h-4 text-gray-700 dark:text-gray-300" />
        </button>
        <button
          onClick={zoomOut}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-600"
          title="Zoom arrière"
        >
          <ZoomOut className="w-4 h-4 text-gray-700 dark:text-gray-300" />
        </button>
        <button
          onClick={resetView}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-600"
          title="Réinitialiser la vue"
        >
          <Maximize className="w-4 h-4 text-gray-700 dark:text-gray-300" />
        </button>
        <button
          onClick={() => setShowLabels(!showLabels)}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-600"
          title={showLabels ? "Masquer les labels" : "Afficher les labels"}
        >
          <Tag className="w-4 h-4 text-gray-700 dark:text-gray-300" />
        </button>
        <button
          onClick={() => setPhysicsEnabled(!physicsEnabled)}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-600"
          title={physicsEnabled ? "Désactiver la physique" : "Activer la physique"}
        >
          {physicsEnabled ? (
            <Pause className="w-4 h-4 text-gray-700 dark:text-gray-300" />
          ) : (
            <Play className="w-4 h-4 text-gray-700 dark:text-gray-300" />
          )}
        </button>
        <button
          onClick={exportPNG}
          className="p-2 bg-white dark:bg-gray-800 rounded-lg shadow-md hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-600"
          title="Exporter PNG"
        >
          <Download className="w-4 h-4 text-gray-700 dark:text-gray-300" />
        </button>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-600 p-3">
        <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Légende</p>
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-gray-600 dark:text-gray-400">Personne</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500" />
            <span className="text-gray-600 dark:text-gray-400">Entreprise</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-orange-500 rotate-45" />
            <span className="text-gray-600 dark:text-gray-400">Dossier</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-purple-500" style={{ clipPath: "polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)" }} />
            <span className="text-gray-600 dark:text-gray-400">Avocat</span>
          </div>
        </div>
      </div>
    </div>
  );
}
