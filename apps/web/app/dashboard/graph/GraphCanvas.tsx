"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface GraphNode {
  id: string;
  label: string;
  name: string;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

interface GraphEdge {
  from: string;
  to: string;
  type: string;
}

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  width?: number;
  height?: number;
  onNodeClick?: (node: GraphNode) => void;
}

const NODE_COLORS: Record<string, string> = {
  Person: "#3b82f6",        // blue
  Organization: "#22c55e",  // green
  Case: "#f97316",          // orange
  Document: "#a855f7",      // purple
  Event: "#eab308",         // yellow
  LegalConcept: "#ec4899",  // pink
  Court: "#ef4444",         // red
  Location: "#14b8a6",      // teal
};

const NODE_RADIUS = 24;
const LABEL_OFFSET = 32;

export default function GraphCanvas({
  nodes,
  edges,
  width = 900,
  height = 600,
  onNodeClick,
}: GraphCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [simNodes, setSimNodes] = useState<GraphNode[]>([]);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; node: GraphNode } | null>(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const dragRef = useRef<{ node: GraphNode; startX: number; startY: number } | null>(null);
  const panRef = useRef<{ startX: number; startY: number; tx: number; ty: number } | null>(null);
  const animRef = useRef<number>(0);

  // D3-like force simulation in pure JS
  const simulate = useCallback(() => {
    if (nodes.length === 0) return;

    // Initialize positions
    const simulated: GraphNode[] = nodes.map((n, i) => ({
      ...n,
      x: n.x ?? width / 2 + Math.cos((2 * Math.PI * i) / nodes.length) * 200,
      y: n.y ?? height / 2 + Math.sin((2 * Math.PI * i) / nodes.length) * 200,
      vx: 0,
      vy: 0,
      fx: null,
      fy: null,
    }));

    const nodeMap = new Map(simulated.map((n) => [n.id, n]));
    let alpha = 1;
    const alphaDecay = 0.02;
    const alphaMin = 0.01;

    const tick = () => {
      if (alpha < alphaMin) return;
      alpha *= 1 - alphaDecay;

      // Center gravity
      for (const node of simulated) {
        if (node.fx != null) { node.x = node.fx; continue; }
        if (node.fy != null) { node.y = node.fy; continue; }
        node.vx = (node.vx || 0) + (width / 2 - (node.x || 0)) * 0.01 * alpha;
        node.vy = (node.vy || 0) + (height / 2 - (node.y || 0)) * 0.01 * alpha;
      }

      // Charge repulsion
      for (let i = 0; i < simulated.length; i++) {
        for (let j = i + 1; j < simulated.length; j++) {
          const a = simulated[i];
          const b = simulated[j];
          const dx = (b.x || 0) - (a.x || 0);
          const dy = (b.y || 0) - (a.y || 0);
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = (-300 * alpha) / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          if (a.fx == null) a.vx = (a.vx || 0) - fx;
          if (a.fy == null) a.vy = (a.vy || 0) - fy;
          if (b.fx == null) b.vx = (b.vx || 0) + fx;
          if (b.fy == null) b.vy = (b.vy || 0) + fy;
        }
      }

      // Link spring force
      for (const edge of edges) {
        const source = nodeMap.get(edge.from);
        const target = nodeMap.get(edge.to);
        if (!source || !target) continue;
        const dx = (target.x || 0) - (source.x || 0);
        const dy = (target.y || 0) - (source.y || 0);
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const targetDist = 120;
        const force = ((dist - targetDist) / dist) * 0.1 * alpha;
        const fx = dx * force;
        const fy = dy * force;
        if (source.fx == null) source.vx = (source.vx || 0) + fx;
        if (source.fy == null) source.vy = (source.vy || 0) + fy;
        if (target.fx == null) target.vx = (target.vx || 0) - fx;
        if (target.fy == null) target.vy = (target.vy || 0) - fy;
      }

      // Apply velocity with damping
      for (const node of simulated) {
        if (node.fx != null && node.fy != null) continue;
        node.vx = (node.vx || 0) * 0.6;
        node.vy = (node.vy || 0) * 0.6;
        node.x = (node.x || 0) + (node.vx || 0);
        node.y = (node.y || 0) + (node.vy || 0);
      }

      setSimNodes([...simulated]);
      animRef.current = requestAnimationFrame(tick);
    };

    animRef.current = requestAnimationFrame(tick);
    setSimNodes(simulated);

    return () => cancelAnimationFrame(animRef.current);
  }, [nodes, edges, width, height]);

  useEffect(() => {
    const cleanup = simulate();
    return () => cleanup?.();
  }, [simulate]);

  // Wheel zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const scaleChange = e.deltaY > 0 ? 0.9 : 1.1;
    setTransform((t) => ({
      ...t,
      scale: Math.max(0.2, Math.min(3, t.scale * scaleChange)),
    }));
  };

  // Pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    panRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      tx: transform.x,
      ty: transform.y,
    };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    // Handle dragging a node
    if (dragRef.current) {
      const rect = svgRef.current?.getBoundingClientRect();
      if (!rect) return;
      const x = (e.clientX - rect.left - transform.x) / transform.scale;
      const y = (e.clientY - rect.top - transform.y) / transform.scale;
      dragRef.current.node.fx = x;
      dragRef.current.node.fy = y;
      dragRef.current.node.x = x;
      dragRef.current.node.y = y;
      setSimNodes((prev) => [...prev]);
      return;
    }

    // Handle panning
    if (panRef.current) {
      const dx = e.clientX - panRef.current.startX;
      const dy = e.clientY - panRef.current.startY;
      setTransform((t) => ({
        ...t,
        x: panRef.current!.tx + dx,
        y: panRef.current!.ty + dy,
      }));
    }
  };

  const handleMouseUp = () => {
    if (dragRef.current) {
      dragRef.current.node.fx = null;
      dragRef.current.node.fy = null;
      dragRef.current = null;
    }
    panRef.current = null;
  };

  // Node drag
  const handleNodeMouseDown = (e: React.MouseEvent, node: GraphNode) => {
    e.stopPropagation();
    dragRef.current = { node, startX: e.clientX, startY: e.clientY };
  };

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded-xl border border-gray-200 text-gray-500">
        Aucun noeud dans le graphe. Sélectionnez un dossier et lancez l&apos;analyse.
      </div>
    );
  }

  const nodeMap = new Map(simNodes.map((n) => [n.id, n]));

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="bg-gray-50 rounded-xl border border-gray-200 cursor-grab active:cursor-grabbing"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <g transform={`translate(${transform.x},${transform.y}) scale(${transform.scale})`}>
          {/* Edges */}
          {edges.map((edge, i) => {
            const source = nodeMap.get(edge.from);
            const target = nodeMap.get(edge.to);
            if (!source || !target) return null;
            const mx = ((source.x || 0) + (target.x || 0)) / 2;
            const my = ((source.y || 0) + (target.y || 0)) / 2;
            return (
              <g key={`edge-${i}`}>
                <line
                  x1={source.x || 0}
                  y1={source.y || 0}
                  x2={target.x || 0}
                  y2={target.y || 0}
                  stroke="#94a3b8"
                  strokeWidth={1.5}
                  strokeOpacity={0.6}
                />
                <text
                  x={mx}
                  y={my - 6}
                  textAnchor="middle"
                  fontSize={9}
                  fill="#64748b"
                  className="select-none pointer-events-none"
                >
                  {edge.type}
                </text>
              </g>
            );
          })}

          {/* Nodes */}
          {simNodes.map((node) => (
            <g
              key={node.id}
              transform={`translate(${node.x || 0},${node.y || 0})`}
              onMouseDown={(e) => handleNodeMouseDown(e, node)}
              onMouseEnter={(e) => setTooltip({ x: e.clientX, y: e.clientY, node })}
              onMouseLeave={() => setTooltip(null)}
              onClick={() => onNodeClick?.(node)}
              className="cursor-pointer"
            >
              <circle
                r={NODE_RADIUS}
                fill={NODE_COLORS[node.label] || "#6b7280"}
                stroke="white"
                strokeWidth={2}
                opacity={0.9}
              />
              <text
                y={4}
                textAnchor="middle"
                fontSize={10}
                fill="white"
                fontWeight="bold"
                className="select-none pointer-events-none"
              >
                {node.name.slice(0, 3).toUpperCase()}
              </text>
              <text
                y={LABEL_OFFSET}
                textAnchor="middle"
                fontSize={10}
                fill="#374151"
                className="select-none pointer-events-none"
              >
                {node.name.length > 15 ? node.name.slice(0, 15) + "..." : node.name}
              </text>
            </g>
          ))}
        </g>
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="absolute bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs pointer-events-none z-50"
          style={{ left: tooltip.x - 60, top: tooltip.y - 80 }}
        >
          <p className="font-semibold text-gray-900">{tooltip.node.name}</p>
          <p className="text-gray-500">{tooltip.node.label}</p>
          <p className="text-gray-400 text-[10px]">{tooltip.node.id.slice(0, 8)}...</p>
        </div>
      )}
    </div>
  );
}
