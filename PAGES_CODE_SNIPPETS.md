# Premium Pages - Code Snippets & Examples

## Quick Reference: Component Usage

### 1. Card Component

**Basic Usage:**
```tsx
import { Card } from "@/components/ui";

<Card>
  <p>Card content goes here</p>
</Card>
```

**With Hover & Header:**
```tsx
<Card hover header={<h2>Card Title</h2>}>
  <p>Card content with hover effect</p>
</Card>
```

**In Search Results:**
```tsx
<Card hover className="cursor-pointer group" onClick={() => navigateTo(result.id)}>
  <div className="space-y-3">
    <div className="flex items-start justify-between gap-4">
      <h3 className="text-lg font-semibold text-neutral-900 group-hover:text-accent">
        {result.title}
      </h3>
      <Badge variant="accent">{Math.round(result.score * 100)}%</Badge>
    </div>
    <p className="text-neutral-600">{result.excerpt}</p>
  </div>
</Card>
```

---

### 2. Button Component

**Variants:**
```tsx
import { Button } from "@/components/ui";

// Primary (default)
<Button>Click me</Button>

// Secondary
<Button variant="secondary">Click me</Button>

// Ghost
<Button variant="ghost">Click me</Button>

// Danger
<Button variant="danger">Delete</Button>
```

**With Icon & Loading:**
```tsx
<Button
  icon={<Send className="w-4 h-4" />}
  loading={isLoading}
  disabled={isLoading || !input.trim()}
  onClick={handleSend}
>
  Send
</Button>
```

**All Sizes:**
```tsx
<Button size="sm">Small</Button>
<Button size="md">Medium (default)</Button>
<Button size="lg">Large</Button>
```

---

### 3. Input Component

**Basic:**
```tsx
import { Input } from "@/components/ui";

<Input
  type="text"
  placeholder="Enter search..."
  value={query}
  onChange={(e) => setQuery(e.target.value)}
/>
```

**With Label & Error:**
```tsx
<Input
  label="Email"
  type="email"
  placeholder="you@example.com"
  error={errors.email}
  disabled={isSubmitting}
/>
```

**With Icons:**
```tsx
<Input
  prefixIcon={<Search className="w-5 h-5" />}
  suffixIcon={<X className="w-5 h-5" />}
  placeholder="Search..."
/>
```

**Large Search Bar:**
```tsx
<Input
  type="text"
  placeholder="Recherchez des contrats, clauses, directives..."
  value={query}
  onChange={(e) => setQuery(e.target.value)}
  prefixIcon={<Search className="w-5 h-5" />}
  className="text-lg py-3 pr-12"
/>
```

---

### 4. Badge Component

**Variants:**
```tsx
import { Badge } from "@/components/ui";

<Badge variant="default">Default</Badge>
<Badge variant="success">Success</Badge>
<Badge variant="warning">Warning</Badge>
<Badge variant="danger">Danger</Badge>
<Badge variant="accent">Accent</Badge>
<Badge variant="neutral">Neutral</Badge>
```

**With Dot:**
```tsx
<Badge variant="success" dot>Online</Badge>
<Badge variant="danger" dot pulse>Offline</Badge>
```

**Sizes:**
```tsx
<Badge size="sm">Small</Badge>
<Badge size="md">Medium (default)</Badge>
```

**In Results:**
```tsx
{results.map((result) => (
  <div key={result.id} className="flex items-center gap-2">
    <h3>{result.title}</h3>
    <Badge variant="accent" size="sm">
      {Math.round(result.score * 100)}%
    </Badge>
    <Badge variant="warning" size="sm">
      {result.category}
    </Badge>
  </div>
))}
```

---

### 5. Tabs Component

**Basic Usage:**
```tsx
import { Tabs } from "@/components/ui";

const tabs = [
  {
    id: "tab1",
    label: "Tab 1",
    content: <Component1 />
  },
  {
    id: "tab2",
    label: "Tab 2",
    content: <Component2 />
  }
];

<Tabs tabs={tabs} defaultTab="tab1" />
```

**With Icons & Badges:**
```tsx
const tabs = [
  {
    id: "search",
    label: "Search",
    icon: <Search className="w-4 h-4" />,
    content: <SearchTab />
  },
  {
    id: "chat",
    label: "Chat",
    icon: <MessageSquare className="w-4 h-4" />,
    badge: 3,  // Shows notification count
    content: <ChatTab />
  },
  {
    id: "explain",
    label: "Explain",
    icon: <BookOpen className="w-4 h-4" />,
    content: <ExplainTab />
  }
];

<Tabs tabs={tabs} defaultTab="search" />
```

---

## Page-Specific Code Examples

### Search Page Pattern

```tsx
"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { Card, Button, Input, Badge, LoadingSkeleton, ErrorState, EmptyState } from "@/components/ui";

interface SearchResult {
  id: string;
  title: string;
  score: number;
  excerpt: string;
  category: string;
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      // API call here
      const data = await fetch(`/api/search?q=${query}`);
      setResults(data.results);
    } catch (err) {
      setError("Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center py-8">
        <h1 className="text-5xl font-bold mb-2">Recherche</h1>
        <p className="text-neutral-500">Find documents instantly</p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="max-w-3xl mx-auto w-full">
        <Input
          type="text"
          placeholder="Search..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          prefixIcon={<Search className="w-5 h-5" />}
        />
      </form>

      {/* Error State */}
      {error && <ErrorState message={error} />}

      {/* Loading State */}
      {loading && <LoadingSkeleton variant="list" />}

      {/* Results */}
      {!loading && results.length > 0 && (
        <div className="space-y-4">
          {results.map((result) => (
            <Card key={result.id} hover>
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">{result.title}</h3>
                <Badge variant="accent">{Math.round(result.score * 100)}%</Badge>
                <p className="text-neutral-600">{result.excerpt}</p>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && results.length === 0 && <EmptyState />}
    </div>
  );
}
```

---

### AI Hub Pattern

```tsx
"use client";

import { useState, useEffect } from "react";
import { Sparkles, Loader2 } from "lucide-react";
import { Card, Button, Badge } from "@/components/ui";

interface AICard {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  placeholder: string;
}

const AI_CARDS: AICard[] = [
  {
    id: "draft",
    title: "Brouillon IA",
    description: "Generate legal documents",
    icon: <FileText className="w-6 h-6" />,
    placeholder: "Describe what you need..."
  },
  // ... more cards
];

export default function AIHubPage() {
  const [expandedCard, setExpandedCard] = useState<string | null>(null);
  const [selectedCase, setSelectedCase] = useState("");
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleGenerate = async (taskType: string) => {
    if (!selectedCase || !prompt.trim()) return;

    setLoading(true);
    try {
      const response = await fetch("/api/ai/generate", {
        method: "POST",
        body: JSON.stringify({
          case_id: selectedCase,
          task_type: taskType,
          prompt
        })
      });
      const data = await response.json();
      setResult(data.result);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 gap-6">
        {AI_CARDS.map((card) => (
          <Card
            key={card.id}
            hover
            className={expandedCard === card.id ? "ring-2 ring-accent" : ""}
            onClick={() => setExpandedCard(expandedCard === card.id ? null : card.id)}
          >
            <div className="space-y-4">
              {/* Card Header */}
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-lg bg-accent-50 flex items-center justify-center">
                  {card.icon}
                </div>
                <div>
                  <h2 className="text-lg font-semibold">{card.title}</h2>
                  <p className="text-sm text-neutral-500">{card.description}</p>
                </div>
              </div>

              {/* Expanded Content */}
              {expandedCard === card.id && (
                <div className="space-y-3 pt-4 border-t">
                  <select
                    value={selectedCase}
                    onChange={(e) => setSelectedCase(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg"
                  >
                    <option value="">Select case...</option>
                  </select>

                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder={card.placeholder}
                    className="w-full px-3 py-2 border rounded-lg h-28"
                  />

                  <Button
                    onClick={() => handleGenerate(card.id)}
                    loading={loading}
                    className="w-full"
                  >
                    <Sparkles className="w-4 h-4" />
                    Generate
                  </Button>

                  {result && (
                    <div className="bg-neutral-50 rounded p-4 max-h-64 overflow-y-auto">
                      <p className="text-sm text-neutral-700">{result}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
```

---

### Legal RAG Tab Pattern

```tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { Tabs } from "@/components/ui";
import { Search, MessageSquare, BookOpen } from "lucide-react";

export default function LegalRAGPage() {
  const [activeTab, setActiveTab] = useState("search");
  const [searchResults, setSearchResults] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);

  const tabsContent = [
    {
      id: "search",
      label: "Recherche",
      icon: <Search className="w-4 h-4" />,
      content: (
        <div className="space-y-4">
          {/* Search form and results */}
        </div>
      )
    },
    {
      id: "chat",
      label: "Chat",
      icon: <MessageSquare className="w-4 h-4" />,
      badge: chatMessages.length,
      content: (
        <div className="flex flex-col h-96">
          {/* Chat messages and input */}
        </div>
      )
    },
    {
      id: "explain",
      label: "Expliquer",
      icon: <BookOpen className="w-4 h-4" />,
      content: (
        <div className="space-y-4">
          {/* Explain form and result */}
        </div>
      )
    }
  ];

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-5xl font-bold">Legal RAG Premium</h1>
      </div>

      <div className="max-w-4xl mx-auto w-full">
        <Tabs tabs={tabsContent} defaultTab="search" />
      </div>
    </div>
  );
}
```

---

### Graph Page Pattern

```tsx
"use client";

import { useState, useEffect } from "react";
import { Card, Button, Badge } from "@/components/ui";
import { Network } from "lucide-react";

interface Node {
  id: string;
  label: string;
  type: string;
  properties?: Record<string, string>;
}

interface Edge {
  source: string;
  target: string;
  relationship: string;
}

interface GraphData {
  nodes: Node[];
  edges: Edge[];
}

export default function GraphPage() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<Node | null>(null);

  const getConnectedNodes = () => {
    if (!selectedEntity || !graphData) return [];
    const ids = new Set<string>();
    graphData.edges.forEach((e) => {
      if (e.source === selectedEntity.id) ids.add(e.target);
      if (e.target === selectedEntity.id) ids.add(e.source);
    });
    return graphData.nodes.filter((n) => ids.has(n.id));
  };

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-3 gap-6">
        {/* Main Visualization */}
        <div className="col-span-2">
          <Card>
            <div className="bg-gradient-to-br from-accent-50 to-accent-100 rounded h-96 flex items-center justify-center">
              <div className="text-center">
                <Network className="w-16 h-16 text-accent-300 mx-auto mb-4" />
                <p>Graph Visualization</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Details Sidebar */}
        <div>
          {selectedEntity ? (
            <Card>
              <div className="space-y-4">
                <h2 className="text-lg font-bold">{selectedEntity.label}</h2>
                <Badge variant="accent">{selectedEntity.type}</Badge>

                {selectedEntity.properties && (
                  <div>
                    <p className="text-xs font-semibold uppercase mb-2">Properties</p>
                    {Object.entries(selectedEntity.properties).map(([key, value]) => (
                      <div key={key} className="text-sm">
                        <p className="text-neutral-500">{key}</p>
                        <p className="font-medium">{value}</p>
                      </div>
                    ))}
                  </div>
                )}

                {getConnectedNodes().length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase mb-2">
                      Connected ({getConnectedNodes().length})
                    </p>
                    {getConnectedNodes().map((node) => (
                      <button
                        key={node.id}
                        onClick={() => setSelectedEntity(node)}
                        className="w-full text-left p-2 rounded hover:bg-neutral-50"
                      >
                        <p className="font-medium">{node.label}</p>
                        <Badge size="sm">{node.type}</Badge>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </Card>
          ) : (
            <Card>
              <p className="text-neutral-600">Click entity to view details</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
```

---

## Common Patterns

### Loading State Pattern
```tsx
{loading && <LoadingSkeleton variant="list" />}
{!loading && items.length > 0 && (
  <div className="space-y-4">
    {items.map((item) => <ItemCard key={item.id} item={item} />)}
  </div>
)}
{!loading && items.length === 0 && <EmptyState />}
```

### Error Handling Pattern
```tsx
const [error, setError] = useState<string | null>(null);

try {
  const data = await fetch("/api/...");
  setResults(data);
} catch (err) {
  setError(err.message);
} finally {
  setLoading(false);
}

{error && <ErrorState message={error} onRetry={() => setError(null)} />}
```

### Modal/Expandable Pattern
```tsx
const [expanded, setExpanded] = useState<string | null>(null);

{expanded === id && (
  <div className="space-y-3 pt-4 border-t">
    {/* Expanded content */}
  </div>
)}
```

### API Fetch Pattern
```tsx
import { apiFetch } from "@/lib/api";

const data = await apiFetch<ResponseType>(
  "/endpoint",
  token,
  {
    method: "POST",
    tenantId,
    body: JSON.stringify({ /* data */ })
  }
);
```

---

## Styling Patterns

### Responsive Grid
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {/* Items */}
</div>
```

### Centered Container
```tsx
<div className="max-w-3xl mx-auto w-full">
  {/* Content */}
</div>
```

### Hover Effects
```tsx
<div className="hover:shadow-md hover:-translate-y-1 transition-all duration-normal">
  {/* Content */}
</div>
```

### Focus Ring
```tsx
<input
  className="focus:outline-none focus:ring-2 focus:ring-accent-200"
/>
```

### Dark Mode Support
```tsx
<div className="dark:bg-neutral-900 dark:text-white">
  {/* Content */}
</div>
```

---

**Last Updated**: February 17, 2026
**Total Snippets**: 20+
**Status**: Ready for Copy-Paste ✅
