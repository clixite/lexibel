/**
 * TypeScript types for Legal RAG system
 * Mirrors backend Pydantic schemas from apps/api/schemas/legal_rag.py
 */

export interface LegalEntity {
  entity_type: string; // "article", "law", "case"
  text: string;
  normalized: string;
  confidence: number;
}

export interface LegalSearchResultItem {
  chunk_text: string;
  score: number;
  source: string;
  document_type: string;
  jurisdiction: string;
  article_number?: string;
  date_published?: string;
  url?: string;
  page_number?: number;
  highlighted_passages: string[];
  related_articles: string[];
  entities: LegalEntity[];
}

export interface LegalSearchResponse {
  query: string;
  expanded_query?: string;
  results: LegalSearchResultItem[];
  total: number;
  search_time_ms: number;
  suggested_queries: string[];
  detected_entities: LegalEntity[];
}

export interface LegalSearchParams {
  q: string;
  jurisdiction?: string;
  document_type?: string;
  limit?: number;
  enable_reranking?: boolean;
  enable_multilingual?: boolean;
}

export interface LegalChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources: LegalSearchResultItem[];
}

export interface LegalChatRequest {
  message: string;
  case_id?: string;
  conversation_id?: string;
  max_tokens?: number;
}

export interface LegalChatResponse {
  message: LegalChatMessage;
  conversation_id: string;
  related_documents: LegalSearchResultItem[];
  suggested_followups: string[];
}

export interface ExplainArticleRequest {
  article_text: string;
  simplification_level: 'basic' | 'medium' | 'detailed';
}

export interface ExplainArticleResponse {
  original_text: string;
  simplified_explanation: string;
  key_points: string[];
  related_articles: string[];
}
