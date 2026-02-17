"use client";

import { useEffect, useRef, useState } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import cola from "cytoscape-cola";
import {
  cytoscapeStylesheet,
  cytoscapeConfig,
  layoutConfigs,
  DEFAULT_LAYOUT,
} from "@/lib/graph/cytoscape-config";

// Register layout
if (typeof cytoscape !== "undefined") {
  cytoscape.use(cola);
}

export interface GraphVisualizationProps {
  elements: ElementDefinition[];
  layout?: string;
  onNodeClick?: (nodeData: any) => void;
  onEdgeClick?: (edgeData: any) => void;
  onBackgroundClick?: () => void;
  className?: string;
  height?: number;
}

export default function GraphVisualization({
  elements,
  layout = DEFAULT_LAYOUT,
  onNodeClick,
  onEdgeClick,
  onBackgroundClick,
  className = "",
  height = 600,
}: GraphVisualizationProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [isReady, setIsReady] = useState(false);

  // Initialize Cytoscape
  useEffect(() => {
    if (!containerRef.current || cyRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: [],
      style: cytoscapeStylesheet,
      ...cytoscapeConfig,
    });

    cyRef.current = cy;
    setIsReady(true);

    // Event listeners
    cy.on("tap", "node", (event) => {
      const node = event.target;
      onNodeClick?.(node.data());
    });

    cy.on("tap", "edge", (event) => {
      const edge = event.target;
      onEdgeClick?.(edge.data());
    });

    cy.on("tap", (event) => {
      if (event.target === cy) {
        onBackgroundClick?.();
      }
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
      setIsReady(false);
    };
  }, [onNodeClick, onEdgeClick, onBackgroundClick]);

  // Update elements
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !isReady) return;

    cy.elements().remove();
    cy.add(elements);
    cy.layout(layoutConfigs[layout] || layoutConfigs[DEFAULT_LAYOUT]).run();
  }, [elements, layout, isReady]);

  // Expose methods via ref
  useEffect(() => {
    if (isReady && cyRef.current) {
      (window as any).cy = cyRef.current; // For debugging
    }
  }, [isReady]);

  return (
    <div
      ref={containerRef}
      className={`bg-neutral-50 rounded-lg border border-neutral-200 ${className}`}
      style={{ height: `${height}px` }}
    />
  );
}

// Helper hook to access Cytoscape instance
export function useCytoscapeInstance() {
  return (window as any).cy as Core | undefined;
}
