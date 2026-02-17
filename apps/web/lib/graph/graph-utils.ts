import type { ElementDefinition } from "cytoscape";
import { scaleLinear } from "d3-scale";

// Backend graph data types
export interface GraphNode {
  id: string;
  name: string;
  label: string;
  entity_type?: string;
  properties?: Record<string, any>;
}

export interface GraphEdge {
  from: string;
  to: string;
  type: string;
  from_id?: string;
  to_id?: string;
  relationship_type?: string;
  properties?: Record<string, any>;
}

export interface GraphData {
  nodes: GraphNode[];
  relationships: GraphEdge[];
}

// Conflict types
export interface ConflictDetection {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  conflict_type: string;
  description: string;
  severity: "low" | "medium" | "high" | "critical";
  related_entities: string[];
}

export interface ConflictPrediction {
  entity_pair: [string, string];
  entity_names: [string, string];
  conflict_probability: number;
  risk_factors: string[];
  recommended_actions: string[];
}

// Network statistics
export interface NetworkStats {
  total_nodes: number;
  total_edges: number;
  density: number;
  avg_degree: number;
  max_degree: number;
  connected_components: number;
  diameter: number;
  avg_clustering: number;
}

/**
 * Transform backend graph data to Cytoscape elements
 */
export function transformToCytoscapeElements(
  data: GraphData,
  conflicts?: ConflictDetection[]
): ElementDefinition[] {
  const elements: ElementDefinition[] = [];

  // Create conflict map for quick lookup
  const conflictMap = new Map<string, ConflictDetection[]>();
  conflicts?.forEach((conflict) => {
    const existing = conflictMap.get(conflict.entity_id) || [];
    conflictMap.set(conflict.entity_id, [...existing, conflict]);
  });

  // Add nodes
  data.nodes.forEach((node) => {
    const nodeConflicts = conflictMap.get(node.id) || [];
    const hasConflicts = nodeConflicts.length > 0;
    const riskLevel = hasConflicts
      ? calculateRiskLevel(nodeConflicts)
      : undefined;

    elements.push({
      data: {
        id: node.id,
        name: node.name,
        label: node.label,
        entity_type: node.entity_type || node.label,
        has_conflicts: hasConflicts ? "true" : "false",
        risk_level: riskLevel,
        conflict_count: nodeConflicts.length,
        conflicts: nodeConflicts,
        ...node.properties,
      },
      classes: hasConflicts ? "has-conflicts" : "",
    });
  });

  // Add edges
  data.relationships.forEach((edge, index) => {
    const sourceId = edge.from_id || edge.from;
    const targetId = edge.to_id || edge.to;
    const relType = edge.relationship_type || edge.type;

    elements.push({
      data: {
        id: `edge-${index}`,
        source: sourceId,
        target: targetId,
        relationship_type: relType,
        ...edge.properties,
      },
    });
  });

  return elements;
}

/**
 * Calculate risk level from conflicts
 */
export function calculateRiskLevel(
  conflicts: ConflictDetection[]
): "low" | "medium" | "high" | "critical" {
  if (conflicts.length === 0) return "low";

  const severityScores = {
    low: 1,
    medium: 2,
    high: 3,
    critical: 4,
  };

  const maxSeverity = Math.max(
    ...conflicts.map((c) => severityScores[c.severity])
  );

  if (maxSeverity >= 4) return "critical";
  if (maxSeverity >= 3) return "high";
  if (maxSeverity >= 2) return "medium";
  return "low";
}

/**
 * Calculate risk score (0-100) from conflicts
 */
export function calculateRiskScore(conflicts: ConflictDetection[]): number {
  if (conflicts.length === 0) return 0;

  const severityWeights = {
    low: 10,
    medium: 25,
    high: 50,
    critical: 100,
  };

  const totalScore = conflicts.reduce(
    (sum, conflict) => sum + severityWeights[conflict.severity],
    0
  );

  return Math.min(100, totalScore);
}

/**
 * Get severity color
 */
export function getSeverityColor(
  severity: "low" | "medium" | "high" | "critical"
): string {
  const colors = {
    low: "#22c55e", // green-500
    medium: "#f97316", // orange-500
    high: "#ef4444", // red-500
    critical: "#991b1b", // red-900
  };
  return colors[severity];
}

/**
 * Get severity label
 */
export function getSeverityLabel(
  severity: "low" | "medium" | "high" | "critical"
): string {
  const labels = {
    low: "Faible",
    medium: "Moyen",
    high: "Élevé",
    critical: "Critique",
  };
  return labels[severity];
}

/**
 * Create color scale for risk scores
 */
export function createRiskColorScale() {
  return scaleLinear<string>()
    .domain([0, 33, 66, 100])
    .range(["#22c55e", "#eab308", "#f97316", "#ef4444"]);
}

/**
 * Filter graph by entity type
 */
export function filterByEntityType(
  elements: ElementDefinition[],
  entityTypes: string[]
): ElementDefinition[] {
  if (entityTypes.length === 0) return elements;

  const filteredNodes = elements.filter(
    (el) =>
      !el.data.source &&
      !el.data.target &&
      entityTypes.includes(el.data.entity_type)
  );

  const nodeIds = new Set(filteredNodes.map((n) => n.data.id));

  const filteredEdges = elements.filter(
    (el) =>
      el.data.source &&
      el.data.target &&
      nodeIds.has(el.data.source) &&
      nodeIds.has(el.data.target)
  );

  return [...filteredNodes, ...filteredEdges];
}

/**
 * Find shortest path between two nodes
 */
export function findShortestPath(
  elements: ElementDefinition[],
  sourceId: string,
  targetId: string
): string[] {
  // Build adjacency list
  const adjacency = new Map<string, string[]>();
  elements.forEach((el) => {
    if (el.data.source && el.data.target) {
      const neighbors = adjacency.get(el.data.source) || [];
      adjacency.set(el.data.source, [...neighbors, el.data.target]);
    }
  });

  // BFS to find shortest path
  const queue: [string, string[]][] = [[sourceId, [sourceId]]];
  const visited = new Set<string>([sourceId]);

  while (queue.length > 0) {
    const [current, path] = queue.shift()!;

    if (current === targetId) {
      return path;
    }

    const neighbors = adjacency.get(current) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push([neighbor, [...path, neighbor]]);
      }
    }
  }

  return []; // No path found
}

/**
 * Get node neighbors
 */
export function getNodeNeighbors(
  elements: ElementDefinition[],
  nodeId: string,
  depth = 1
): Set<string> {
  const neighbors = new Set<string>();

  function traverse(id: string, currentDepth: number) {
    if (currentDepth > depth) return;

    elements.forEach((el) => {
      if (el.data.source === id && !neighbors.has(el.data.target)) {
        neighbors.add(el.data.target);
        traverse(el.data.target, currentDepth + 1);
      } else if (el.data.target === id && !neighbors.has(el.data.source)) {
        neighbors.add(el.data.source);
        traverse(el.data.source, currentDepth + 1);
      }
    });
  }

  traverse(nodeId, 1);
  return neighbors;
}

/**
 * Calculate centrality scores (degree centrality)
 */
export function calculateCentrality(
  elements: ElementDefinition[]
): Map<string, number> {
  const centrality = new Map<string, number>();

  // Count degree for each node
  elements.forEach((el) => {
    if (!el.data.source && !el.data.target && el.data.id) {
      centrality.set(el.data.id, 0);
    }
  });

  elements.forEach((el) => {
    if (el.data.source && el.data.target) {
      centrality.set(
        el.data.source,
        (centrality.get(el.data.source) || 0) + 1
      );
      centrality.set(
        el.data.target,
        (centrality.get(el.data.target) || 0) + 1
      );
    }
  });

  return centrality;
}

/**
 * Export graph to JSON
 */
export function exportGraphToJSON(elements: ElementDefinition[]): string {
  return JSON.stringify(
    {
      nodes: elements.filter((el) => !el.data.source && !el.data.target),
      edges: elements.filter((el) => el.data.source && el.data.target),
    },
    null,
    2
  );
}

/**
 * Format large numbers
 */
export function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  } else if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toString();
}

/**
 * Format percentage
 */
export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
