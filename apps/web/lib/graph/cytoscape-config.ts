import type { Stylesheet, LayoutOptions } from "cytoscape";

// Node colors by entity type
export const NODE_COLORS: Record<string, string> = {
  Person: "#3b82f6", // blue-500
  Organization: "#22c55e", // green-500
  Case: "#f97316", // orange-500
  Document: "#a855f7", // purple-500
  Event: "#eab308", // yellow-500
  LegalConcept: "#ec4899", // pink-500
  Court: "#ef4444", // red-500
  Location: "#14b8a6", // teal-500
  default: "#6b7280", // gray-500
};

// Node shapes by entity type
export const NODE_SHAPES: Record<string, string> = {
  Person: "ellipse",
  Organization: "rectangle",
  Case: "diamond",
  Document: "rectangle",
  Event: "triangle",
  LegalConcept: "hexagon",
  Court: "octagon",
  Location: "round-rectangle",
  default: "ellipse",
};

// Edge colors by relationship type
export const EDGE_COLORS: Record<string, string> = {
  REPRESENTS: "#3b82f6",
  RELATED_TO: "#6b7280",
  WORKS_FOR: "#22c55e",
  LOCATED_IN: "#14b8a6",
  PART_OF: "#a855f7",
  MENTIONS: "#f97316",
  CONFLICTS_WITH: "#ef4444",
  default: "#94a3b8",
};

// Cytoscape stylesheet
export const cytoscapeStylesheet: Stylesheet[] = [
  // Node base styles
  {
    selector: "node",
    style: {
      backgroundColor: (ele: any) =>
        NODE_COLORS[ele.data("entity_type")] || NODE_COLORS.default,
      shape: (ele: any) =>
        NODE_SHAPES[ele.data("entity_type")] || NODE_SHAPES.default,
      label: "data(name)",
      "text-valign": "center",
      "text-halign": "center",
      "font-size": "12px",
      "font-weight": "500",
      color: "#ffffff",
      "text-outline-color": (ele: any) =>
        NODE_COLORS[ele.data("entity_type")] || NODE_COLORS.default,
      "text-outline-width": 2,
      width: 60,
      height: 60,
      "border-width": 3,
      "border-color": "#ffffff",
      "overlay-padding": 6,
    },
  },

  // Selected node
  {
    selector: "node:selected",
    style: {
      "border-color": "#fbbf24",
      "border-width": 4,
    },
  },

  // High-risk node
  {
    selector: "node[risk_level = 'high']",
    style: {
      "border-color": "#ef4444",
      "border-width": 5,
      "border-style": "double",
    },
  },

  // Medium-risk node
  {
    selector: "node[risk_level = 'medium']",
    style: {
      "border-color": "#f97316",
      "border-width": 4,
    },
  },

  // Conflict node
  {
    selector: "node[has_conflicts = 'true']",
    style: {
      "background-image": "data(icon)",
      "background-fit": "cover cover",
      "background-clip": "none",
    },
  },

  // Edge base styles
  {
    selector: "edge",
    style: {
      width: 2,
      "line-color": (ele: any) =>
        EDGE_COLORS[ele.data("relationship_type")] || EDGE_COLORS.default,
      "target-arrow-color": (ele: any) =>
        EDGE_COLORS[ele.data("relationship_type")] || EDGE_COLORS.default,
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      label: "data(relationship_type)",
      "font-size": "10px",
      color: "#64748b",
      "text-background-color": "#ffffff",
      "text-background-opacity": 0.8,
      "text-background-padding": 3,
      "text-background-shape": "roundrectangle",
      "text-rotation": "autorotate",
      "edge-text-rotation": "autorotate",
    },
  },

  // Selected edge
  {
    selector: "edge:selected",
    style: {
      width: 4,
      "line-color": "#fbbf24",
      "target-arrow-color": "#fbbf24",
    },
  },

  // Conflict edge
  {
    selector: "edge[relationship_type = 'CONFLICTS_WITH']",
    style: {
      width: 3,
      "line-color": "#ef4444",
      "line-style": "dashed",
      "target-arrow-color": "#ef4444",
    },
  },

  // Hovered node
  {
    selector: "node:active",
    style: {
      "overlay-color": "#fbbf24",
      "overlay-opacity": 0.2,
    },
  },
];

// Layout configurations
export const layoutConfigs: Record<string, LayoutOptions> = {
  // Force-directed layout (default)
  cola: {
    name: "cola",
    animate: true,
    animationDuration: 1000,
    nodeSpacing: 80,
    edgeLength: 150,
    fit: true,
    padding: 50,
    randomize: false,
    avoidOverlap: true,
    handleDisconnected: true,
    convergenceThreshold: 0.01,
    infinite: false,
  },

  // Hierarchical layout
  breadthfirst: {
    name: "breadthfirst",
    directed: true,
    spacingFactor: 1.5,
    animate: true,
    animationDuration: 1000,
    fit: true,
    padding: 50,
  },

  // Circular layout
  circle: {
    name: "circle",
    animate: true,
    animationDuration: 1000,
    fit: true,
    padding: 50,
    spacingFactor: 1.5,
  },

  // Concentric layout
  concentric: {
    name: "concentric",
    animate: true,
    animationDuration: 1000,
    fit: true,
    padding: 50,
    spacingFactor: 1.5,
    concentric: (node: any) => node.degree(),
    levelWidth: () => 2,
  },

  // Grid layout
  grid: {
    name: "grid",
    animate: true,
    animationDuration: 1000,
    fit: true,
    padding: 50,
    spacingFactor: 1.5,
  },

  // Preset layout (use existing positions)
  preset: {
    name: "preset",
    animate: false,
    fit: true,
    padding: 50,
  },
};

// Default layout
export const DEFAULT_LAYOUT = "cola";

// Cytoscape configuration
export const cytoscapeConfig = {
  minZoom: 0.1,
  maxZoom: 3,
  wheelSensitivity: 0.2,
  boxSelectionEnabled: true,
  autounselectify: false,
  autoungrabify: false,
  hideEdgesOnViewport: false,
  textureOnViewport: false,
  motionBlur: false,
  pixelRatio: "auto" as const,
};

// Export preset
export const exportPresets = {
  png: {
    output: "blob" as const,
    bg: "#ffffff",
    full: true,
    scale: 2,
  },
  jpg: {
    output: "blob" as const,
    bg: "#ffffff",
    full: true,
    scale: 2,
  },
  svg: {
    output: "blob" as const,
    full: true,
  },
};
