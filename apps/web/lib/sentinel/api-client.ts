/**
 * SENTINEL API Client
 *
 * Type-safe client for all SENTINEL conflict detection endpoints.
 */

import { z } from "zod";

// ══════════════════════════════════════════════════════════════════
// SCHEMAS
// ══════════════════════════════════════════════════════════════════

export const ConflictTypeSchema = z.enum([
  "direct_adversary",
  "director_overlap",
  "family_tie",
  "indirect_ownership",
  "group_company",
  "business_partner",
  "historical_conflict",
  "professional_overlap",
]);

export const ConflictStatusSchema = z.enum(["active", "resolved", "dismissed"]);

export const ResolutionTypeSchema = z.enum([
  "refused",
  "waiver_obtained",
  "false_positive",
]);

export const EntityRefSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  type: z.enum(["Person", "Company"]),
});

export const ConflictDetailSchema = z.object({
  id: z.string().uuid(),
  conflict_type: ConflictTypeSchema,
  severity_score: z.number().int().min(0).max(100),
  description: z.string(),
  entities_involved: z.array(EntityRefSchema),
  detected_at: z.string().datetime(),
});

export const ConflictSummarySchema = ConflictDetailSchema.extend({
  status: ConflictStatusSchema,
  resolved_at: z.string().datetime().optional().nullable(),
});

export const GraphNodeSchema = z.object({
  id: z.string(),
  label: z.string(),
  name: z.string(),
  properties: z.record(z.string(), z.any()).optional(),
});

export const GraphEdgeSchema = z.object({
  from: z.string(),
  to: z.string(),
  type: z.string(),
  properties: z.record(z.string(), z.any()).optional(),
});

export const ConflictCheckResponseSchema = z.object({
  conflicts: z.array(ConflictDetailSchema),
  total_count: z.number(),
  highest_severity: z.number().int().min(0).max(100),
  check_timestamp: z.string().datetime(),
  graph_data: z
    .object({
      nodes: z.array(z.any()),
      edges: z.array(z.any()),
    })
    .optional()
    .nullable(),
});

export const ConflictListResponseSchema = z.object({
  conflicts: z.array(ConflictSummarySchema),
  pagination: z.object({
    page: z.number(),
    per_page: z.number(),
    total: z.number(),
    total_pages: z.number(),
  }),
});

export const EntitySearchResultSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  type: z.string(),
  bce_number: z.string().optional().nullable(),
  email: z.string().optional().nullable(),
  phone: z.string().optional().nullable(),
  conflict_count: z.number().int().min(0),
  last_checked: z.string().datetime().optional().nullable(),
});

export const GraphDataResponseSchema = z.object({
  nodes: z.array(GraphNodeSchema),
  edges: z.array(GraphEdgeSchema),
  center_entity_id: z.string().uuid(),
});

// ══════════════════════════════════════════════════════════════════
// TYPES
// ══════════════════════════════════════════════════════════════════

export type ConflictType = z.infer<typeof ConflictTypeSchema>;
export type ConflictStatus = z.infer<typeof ConflictStatusSchema>;
export type ResolutionType = z.infer<typeof ResolutionTypeSchema>;
export type EntityRef = z.infer<typeof EntityRefSchema>;
export type ConflictDetail = z.infer<typeof ConflictDetailSchema>;
export type ConflictSummary = z.infer<typeof ConflictSummarySchema>;
export type GraphNode = z.infer<typeof GraphNodeSchema>;
export type GraphEdge = z.infer<typeof GraphEdgeSchema>;
export type ConflictCheckResponse = z.infer<typeof ConflictCheckResponseSchema>;
export type ConflictListResponse = z.infer<typeof ConflictListResponseSchema>;
export type EntitySearchResult = z.infer<typeof EntitySearchResultSchema>;
export type GraphDataResponse = z.infer<typeof GraphDataResponseSchema>;

// ══════════════════════════════════════════════════════════════════
// API CLIENT
// ══════════════════════════════════════════════════════════════════

const API_BASE = "/api/sentinel";

async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit,
  schema?: z.ZodSchema<T>
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  const data = await response.json();

  if (schema) {
    return schema.parse(data);
  }

  return data;
}

export const sentinelAPI = {
  /**
   * Check for conflicts involving a contact
   */
  checkConflict: async (params: {
    contact_id: string;
    case_id?: string;
    include_graph?: boolean;
  }) => {
    return fetchAPI<ConflictCheckResponse>(
      "/check-conflict",
      {
        method: "POST",
        body: JSON.stringify(params),
      },
      ConflictCheckResponseSchema
    );
  },

  /**
   * List conflicts with pagination and filters
   */
  listConflicts: async (params?: {
    page?: number;
    page_size?: number;
    status?: ConflictStatus | "all";
    severity_min?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set("page", params.page.toString());
    if (params?.page_size) searchParams.set("page_size", params.page_size.toString());
    if (params?.status && params.status !== "all") searchParams.set("status", params.status);
    if (params?.severity_min !== undefined)
      searchParams.set("severity_min", params.severity_min.toString());

    const query = searchParams.toString();
    return fetchAPI<ConflictListResponse>(
      `/conflicts${query ? `?${query}` : ""}`,
      undefined,
      ConflictListResponseSchema
    );
  },

  /**
   * Resolve a conflict
   */
  resolveConflict: async (conflictId: string, resolution: ResolutionType, notes?: string) => {
    return fetchAPI(
      `/conflicts/${conflictId}/resolve`,
      {
        method: "PUT",
        body: JSON.stringify({ resolution, notes }),
      }
    );
  },

  /**
   * Sync entities to graph
   */
  syncGraph: async (params?: {
    entity_ids?: string[];
    sync_all?: boolean;
    limit?: number;
  }) => {
    return fetchAPI("/sync", {
      method: "POST",
      body: JSON.stringify(params || {}),
    });
  },

  /**
   * Get graph data for an entity
   */
  getGraphData: async (entityId: string, depth: 1 | 2 | 3 = 2) => {
    return fetchAPI<GraphDataResponse>(
      `/graph/${entityId}?depth=${depth}`,
      undefined,
      GraphDataResponseSchema
    );
  },

  /**
   * Search entities
   */
  searchEntities: async (params: {
    q: string;
    entity_type?: "Person" | "Company";
    limit?: number;
  }) => {
    const searchParams = new URLSearchParams({ q: params.q });
    if (params.entity_type) searchParams.set("entity_type", params.entity_type);
    if (params.limit) searchParams.set("limit", params.limit.toString());

    return fetchAPI<{ results: EntitySearchResult[]; total: number }>(
      `/search?${searchParams.toString()}`
    );
  },
};
