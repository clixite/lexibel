# Graph Visualization Frontend Guide

## Overview

This guide covers the frontend implementation for LexiBel's Knowledge Graph and Conflict Detection visualization system.

## Technology Stack (2026 Best Practices)

### Core Libraries

**Graph Visualization:**
- **Cytoscape.js** (Recommended) - High-performance, feature-rich, mobile-friendly
- **D3.js** - Custom visualizations, maximum flexibility
- **vis.js** - Easy setup, good defaults
- **react-force-graph** - React wrapper for force-directed graphs

**UI Framework:**
- Next.js 14+ (App Router)
- React 18+
- TypeScript
- Tailwind CSS
- shadcn/ui components

**State Management:**
- TanStack Query (React Query) - Server state
- Zustand - Client state
- React Context - Theme, user settings

**3D Rendering (Optional):**
- Three.js - WebGL 3D graphs for large networks
- react-three-fiber - React wrapper for Three.js

## Directory Structure

```
apps/web/app/
├── dashboard/
│   ├── graph/
│   │   ├── page.tsx                    # Graph overview/network stats
│   │   ├── [caseId]/
│   │   │   ├── page.tsx               # Case graph view
│   │   │   ├── components/
│   │   │   │   ├── GraphVisualization.tsx
│   │   │   │   ├── ConflictExplorer.tsx
│   │   │   │   ├── ConflictPathView.tsx
│   │   │   │   ├── NetworkStats.tsx
│   │   │   │   ├── EntityCard.tsx
│   │   │   │   ├── RelationshipTimeline.tsx
│   │   │   │   └── ConflictPredictionPanel.tsx
│   │   │   └── hooks/
│   │   │       ├── useGraphData.ts
│   │   │       ├── useConflictDetection.ts
│   │   │       └── useConflictPrediction.ts
│   │   └── components/
│   │       ├── GraphLayout.tsx         # Shared graph layout
│   │       ├── NodeRenderer.tsx        # Custom node styles
│   │       ├── EdgeRenderer.tsx        # Custom edge styles
│   │       └── GraphControls.tsx       # Zoom, pan, filters
│   └── cases/
│       └── [id]/
│           └── conflicts/
│               └── page.tsx            # Case-specific conflicts
└── components/
    └── graph/
        ├── ConflictBadge.tsx
        ├── SeverityIndicator.tsx
        └── RiskScoreGauge.tsx
```

## Core Components

### 1. GraphVisualization.tsx

**Purpose:** Main graph rendering component with Cytoscape.js

```typescript
'use client';

import { useEffect, useRef, useState } from 'react';
import cytoscape, { Core, NodeSingular, EdgeSingular } from 'cytoscape';
import { useGraphData } from '../hooks/useGraphData';
import { GraphControls } from './GraphControls';
import { EntityCard } from './EntityCard';

interface GraphVisualizationProps {
  caseId: string;
  highlightConflicts?: boolean;
  interactive?: boolean;
}

export function GraphVisualization({
  caseId,
  highlightConflicts = true,
  interactive = true,
}: GraphVisualizationProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [selectedNode, setSelectedNode] = useState<NodeSingular | null>(null);

  const { data: graphData, isLoading } = useGraphData(caseId);

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    // Initialize Cytoscape
    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        // Nodes
        ...graphData.nodes.map((node) => ({
          data: {
            id: node.id,
            label: node.name,
            type: node.label,
            ...node.properties,
          },
        })),
        // Edges
        ...graphData.relationships.map((rel) => ({
          data: {
            id: `${rel.from}-${rel.to}`,
            source: rel.from,
            target: rel.to,
            type: rel.type,
            ...rel.properties,
          },
        })),
      ],
      style: getGraphStyle(highlightConflicts),
      layout: {
        name: 'cose',
        animate: true,
        animationDuration: 500,
        idealEdgeLength: 100,
        nodeOverlap: 20,
        refresh: 20,
        fit: true,
        padding: 30,
        randomize: false,
        componentSpacing: 100,
        nodeRepulsion: 400000,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 1000,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0,
      },
      userZoomingEnabled: interactive,
      userPanningEnabled: interactive,
      boxSelectionEnabled: false,
    });

    cyRef.current = cy;

    // Event handlers
    if (interactive) {
      cy.on('tap', 'node', (event) => {
        setSelectedNode(event.target);
      });

      cy.on('tap', (event) => {
        if (event.target === cy) {
          setSelectedNode(null);
        }
      });

      // Hover effects
      cy.on('mouseover', 'node', (event) => {
        event.target.addClass('hover');
        // Highlight connected edges
        event.target.connectedEdges().addClass('highlighted');
      });

      cy.on('mouseout', 'node', (event) => {
        event.target.removeClass('hover');
        event.target.connectedEdges().removeClass('highlighted');
      });
    }

    return () => {
      cy.destroy();
    };
  }, [graphData, highlightConflicts, interactive]);

  if (isLoading) {
    return <GraphSkeleton />;
  }

  return (
    <div className="relative h-full w-full">
      <div
        ref={containerRef}
        className="h-full w-full bg-gray-50 dark:bg-gray-900 rounded-lg"
      />

      {interactive && (
        <GraphControls
          cy={cyRef.current}
          onLayoutChange={(layoutName) => {
            cyRef.current?.layout({ name: layoutName }).run();
          }}
        />
      )}

      {selectedNode && (
        <EntityCard
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  );
}

// Graph styling
function getGraphStyle(highlightConflicts: boolean): cytoscape.Stylesheet[] {
  return [
    // Base node style
    {
      selector: 'node',
      style: {
        'background-color': '#3b82f6',
        'label': 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        'font-size': '12px',
        'font-weight': '500',
        'color': '#1f2937',
        'text-outline-color': '#ffffff',
        'text-outline-width': '2px',
        'width': '60px',
        'height': '60px',
        'overlay-opacity': 0,
      },
    },

    // Node types - different colors
    {
      selector: 'node[type="Person"]',
      style: {
        'background-color': '#10b981',
        'shape': 'ellipse',
      },
    },
    {
      selector: 'node[type="Organization"]',
      style: {
        'background-color': '#8b5cf6',
        'shape': 'rectangle',
      },
    },
    {
      selector: 'node[type="Case"]',
      style: {
        'background-color': '#f59e0b',
        'shape': 'diamond',
        'width': '80px',
        'height': '80px',
      },
    },
    {
      selector: 'node[type="Court"]',
      style: {
        'background-color': '#ef4444',
        'shape': 'octagon',
      },
    },
    {
      selector: 'node[type="Document"]',
      style: {
        'background-color': '#06b6d4',
        'shape': 'rectangle',
      },
    },

    // Hover state
    {
      selector: 'node.hover',
      style: {
        'border-width': '4px',
        'border-color': '#1f2937',
        'overlay-opacity': 0.1,
      },
    },

    // Selected state
    {
      selector: 'node:selected',
      style: {
        'border-width': '5px',
        'border-color': '#3b82f6',
      },
    },

    // Edge style
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': '#cbd5e1',
        'target-arrow-color': '#cbd5e1',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'arrow-scale': 1.5,
        'label': 'data(type)',
        'font-size': '10px',
        'color': '#64748b',
        'text-outline-color': '#ffffff',
        'text-outline-width': '2px',
        'text-rotation': 'autorotate',
      },
    },

    // Conflict edges (highlighted)
    ...(highlightConflicts ? [
      {
        selector: 'edge[type="OPPOSED_TO"]',
        style: {
          'line-color': '#ef4444',
          'target-arrow-color': '#ef4444',
          'width': 4,
          'line-style': 'dashed',
        },
      },
      {
        selector: 'edge[type="REPRESENTS"]',
        style: {
          'line-color': '#10b981',
          'target-arrow-color': '#10b981',
          'width': 3,
        },
      },
    ] : []),

    // Highlighted edges
    {
      selector: 'edge.highlighted',
      style: {
        'line-color': '#3b82f6',
        'target-arrow-color': '#3b82f6',
        'width': 4,
      },
    },
  ];
}

function GraphSkeleton() {
  return (
    <div className="h-full w-full bg-gray-50 dark:bg-gray-900 rounded-lg animate-pulse flex items-center justify-center">
      <div className="text-gray-400">Loading graph...</div>
    </div>
  );
}
```

### 2. ConflictExplorer.tsx

**Purpose:** Interactive conflict detection and exploration

```typescript
'use client';

import { useState } from 'react';
import { useConflictDetection } from '../hooks/useConflictDetection';
import { SeverityIndicator } from '@/components/graph/SeverityIndicator';
import { RiskScoreGauge } from '@/components/graph/RiskScoreGauge';
import { ConflictPathView } from './ConflictPathView';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AlertTriangle, Network, TrendingUp } from 'lucide-react';

interface ConflictExplorerProps {
  caseId: string;
}

export function ConflictExplorer({ caseId }: ConflictExplorerProps) {
  const [maxDepth, setMaxDepth] = useState(3);
  const [minConfidence, setMinConfidence] = useState(0.3);

  const { data: report, isLoading, refetch } = useConflictDetection(
    caseId,
    maxDepth,
    minConfidence
  );

  if (isLoading) {
    return <ConflictSkeleton />;
  }

  if (!report) {
    return <div>No conflict data available</div>;
  }

  const criticalConflicts = report.conflicts.filter(
    (c) => c.severity === 'critical'
  );
  const highConflicts = report.conflicts.filter((c) => c.severity === 'high');

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Conflicts
            </CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{report.total_conflicts}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {criticalConflicts.length} critical, {highConflicts.length} high
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Network Density
            </CardTitle>
            <Network className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(report.network_analysis.density * 100).toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {report.network_analysis.total_relationships} relationships
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Risk Level
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {criticalConflicts.length > 0
                ? 'Critical'
                : highConflicts.length > 0
                ? 'High'
                : 'Low'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Based on severity analysis
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Detection Settings</CardTitle>
        </CardHeader>
        <CardContent className="flex gap-4">
          <div className="flex-1">
            <label className="text-sm font-medium">Max Depth (Hops)</label>
            <select
              value={maxDepth}
              onChange={(e) => setMaxDepth(Number(e.target.value))}
              className="w-full mt-1 border rounded px-3 py-2"
            >
              <option value={1}>1 hop (Direct only)</option>
              <option value={2}>2 hops (+ Associates)</option>
              <option value={3}>3 hops (+ Network)</option>
              <option value={4}>4 hops (Deep analysis)</option>
              <option value={5}>5 hops (Maximum)</option>
            </select>
          </div>

          <div className="flex-1">
            <label className="text-sm font-medium">Min Confidence</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={minConfidence}
              onChange={(e) => setMinConfidence(Number(e.target.value))}
              className="w-full mt-3"
            />
            <div className="text-sm text-muted-foreground">
              {(minConfidence * 100).toFixed(0)}%
            </div>
          </div>

          <div className="flex items-end">
            <Button onClick={() => refetch()}>Re-analyze</Button>
          </div>
        </CardContent>
      </Card>

      {/* Recommendations */}
      {report.recommendations.length > 0 && (
        <Card className="border-orange-200 bg-orange-50 dark:bg-orange-950">
          <CardHeader>
            <CardTitle className="text-orange-900 dark:text-orange-100">
              AI Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {report.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-orange-600 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-orange-900 dark:text-orange-100">
                    {rec}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Conflict Tabs */}
      <Tabs defaultValue="all">
        <TabsList>
          <TabsTrigger value="all">
            All ({report.total_conflicts})
          </TabsTrigger>
          <TabsTrigger value="critical">
            Critical ({report.by_severity.critical || 0})
          </TabsTrigger>
          <TabsTrigger value="high">
            High ({report.by_severity.high || 0})
          </TabsTrigger>
          <TabsTrigger value="medium">
            Medium ({report.by_severity.medium || 0})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          {report.conflicts.map((conflict) => (
            <ConflictCard key={conflict.conflict_id} conflict={conflict} />
          ))}
        </TabsContent>

        <TabsContent value="critical" className="space-y-4">
          {criticalConflicts.map((conflict) => (
            <ConflictCard key={conflict.conflict_id} conflict={conflict} />
          ))}
        </TabsContent>

        {/* Similar for high, medium */}
      </Tabs>
    </div>
  );
}

function ConflictCard({ conflict }: { conflict: any }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <SeverityIndicator severity={conflict.severity} />
              <Badge variant="outline">{conflict.conflict_type}</Badge>
              <Badge variant="secondary">{conflict.hop_distance} hops</Badge>
            </div>
            <CardTitle className="text-lg">{conflict.entity_name}</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {conflict.description}
            </p>
          </div>

          <RiskScoreGauge score={conflict.risk_score} size="sm" />
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          {/* Metrics */}
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-muted-foreground">Confidence</div>
              <div className="font-medium">
                {(conflict.confidence * 100).toFixed(0)}%
              </div>
            </div>
            <div>
              <div className="text-muted-foreground">Network Centrality</div>
              <div className="font-medium">
                {(conflict.network_centrality * 100).toFixed(0)}%
              </div>
            </div>
            <div>
              <div className="text-muted-foreground">Related Cases</div>
              <div className="font-medium">
                {conflict.related_cases.length}
              </div>
            </div>
          </div>

          {/* Paths */}
          {conflict.paths.length > 0 && (
            <div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setExpanded(!expanded)}
              >
                {expanded ? 'Hide' : 'Show'} Conflict Paths (
                {conflict.paths.length})
              </Button>

              {expanded && (
                <div className="mt-2 space-y-2">
                  {conflict.paths.map((path: any, i: number) => (
                    <ConflictPathView key={i} path={path} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Recommendations */}
          {conflict.recommendations.length > 0 && (
            <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
              <div className="text-sm font-medium mb-2">Recommendations:</div>
              <ul className="text-sm space-y-1">
                {conflict.recommendations.map((rec: string, i: number) => (
                  <li key={i} className="text-muted-foreground">
                    • {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ConflictSkeleton() {
  return <div className="animate-pulse">Loading conflicts...</div>;
}
```

### 3. ConflictPredictionPanel.tsx

**Purpose:** Predict conflicts for new entities

```typescript
'use client';

import { useState } from 'react';
import { useConflictPrediction } from '../hooks/useConflictPrediction';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { RiskScoreGauge } from '@/components/graph/RiskScoreGauge';
import { AlertTriangle, CheckCircle } from 'lucide-react';

interface ConflictPredictionPanelProps {
  caseId: string;
}

export function ConflictPredictionPanel({ caseId }: ConflictPredictionPanelProps) {
  const [entityId, setEntityId] = useState('');
  const [predict, setPredictEnabled] = useState(false);

  const { data: prediction, isLoading } = useConflictPrediction(
    caseId,
    entityId,
    predict
  );

  const handlePredict = () => {
    if (entityId) {
      setPredictEnabled(true);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Conflict Risk Prediction</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="text-sm font-medium">Entity ID</label>
          <div className="flex gap-2 mt-1">
            <Input
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              placeholder="Enter entity ID to check..."
              onKeyDown={(e) => e.key === 'Enter' && handlePredict()}
            />
            <Button onClick={handlePredict} disabled={!entityId || isLoading}>
              Predict
            </Button>
          </div>
        </div>

        {isLoading && <div className="text-center py-4">Analyzing...</div>}

        {prediction && (
          <div className="space-y-4">
            <div className="flex items-center justify-center">
              <RiskScoreGauge
                score={prediction.risk_probability * 100}
                size="lg"
              />
            </div>

            <div className="text-center">
              <div className="text-lg font-semibold capitalize">
                {prediction.risk_level} Risk
              </div>
              <div className="text-sm text-muted-foreground">
                {(prediction.risk_probability * 100).toFixed(1)}% probability
              </div>
            </div>

            <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg space-y-2">
              {prediction.recommendations.map((rec: string, i: number) => (
                <div key={i} className="flex items-start gap-2">
                  {prediction.risk_level === 'minimal' ||
                  prediction.risk_level === 'low' ? (
                    <CheckCircle className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-orange-600 mt-0.5 flex-shrink-0" />
                  )}
                  <span className="text-sm">{rec}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

## Custom Hooks

### useGraphData.ts

```typescript
import { useQuery } from '@tanstack/react-query';

export function useGraphData(caseId: string) {
  return useQuery({
    queryKey: ['graph', 'case', caseId],
    queryFn: async () => {
      const response = await fetch(`/api/v1/graph/case/${caseId}`);
      if (!response.ok) throw new Error('Failed to fetch graph data');
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
```

### useConflictDetection.ts

```typescript
import { useQuery } from '@tanstack/react-query';

export function useConflictDetection(
  caseId: string,
  maxDepth: number = 3,
  minConfidence: number = 0.3
) {
  return useQuery({
    queryKey: ['conflicts', 'advanced', caseId, maxDepth, minConfidence],
    queryFn: async () => {
      const response = await fetch(
        `/api/v1/graph/case/${caseId}/conflicts/advanced?max_depth=${maxDepth}&min_confidence=${minConfidence}`
      );
      if (!response.ok) throw new Error('Failed to detect conflicts');
      return response.json();
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}
```

### useConflictPrediction.ts

```typescript
import { useQuery } from '@tanstack/react-query';

export function useConflictPrediction(
  caseId: string,
  entityId: string,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: ['conflicts', 'predict', caseId, entityId],
    queryFn: async () => {
      const response = await fetch(
        `/api/v1/graph/case/${caseId}/conflicts/predict/${entityId}`
      );
      if (!response.ok) throw new Error('Failed to predict conflicts');
      return response.json();
    },
    enabled: enabled && !!entityId,
    staleTime: 5 * 60 * 1000,
  });
}
```

## Component Features Checklist

### Graph Visualization
- [x] Force-directed layout
- [x] Custom node shapes by type
- [x] Color-coded nodes
- [x] Interactive zoom/pan
- [x] Node selection
- [x] Hover effects
- [x] Edge labels
- [x] Conflict highlighting
- [ ] 3D mode (optional)
- [ ] Timeline slider
- [ ] Export to PNG/SVG

### Conflict Explorer
- [x] Multi-hop detection
- [x] Severity filtering
- [x] Risk score visualization
- [x] Conflict paths
- [x] AI recommendations
- [x] Adjustable sensitivity
- [ ] Conflict heatmap
- [ ] Export to PDF report
- [ ] Email alerts

### UI/UX Enhancements
- [x] Dark mode support
- [x] Responsive design
- [x] Loading states
- [x] Error handling
- [ ] Keyboard shortcuts
- [ ] Accessibility (ARIA labels)
- [ ] Print-friendly view
- [ ] Tutorial/onboarding

## Performance Optimization

### 1. Virtual Rendering
```typescript
// For large graphs (1000+ nodes)
import { useVirtualization } from '@tanstack/react-virtual';

// Only render visible portion
```

### 2. Web Workers
```typescript
// Offload graph layout computation
const worker = new Worker('/graph-worker.js');
worker.postMessage({ nodes, edges });
worker.onmessage = (e) => setLayoutPositions(e.data);
```

### 3. Memoization
```typescript
const memoizedStyle = useMemo(
  () => getGraphStyle(highlightConflicts),
  [highlightConflicts]
);
```

## Next Steps

1. **Implement base components** (GraphVisualization, ConflictExplorer)
2. **Add interactive features** (node details, path highlighting)
3. **Integrate with backend API**
4. **Add advanced visualizations** (heatmaps, timelines)
5. **Performance testing** with large graphs
6. **User testing and refinement**

## Resources

- [Cytoscape.js Documentation](https://js.cytoscape.org/)
- [D3.js Graph Gallery](https://d3-graph-gallery.com/network.html)
- [vis.js Network](https://visjs.github.io/vis-network/docs/)
- [TanStack Query](https://tanstack.com/query/latest)
- [shadcn/ui](https://ui.shadcn.com/)
