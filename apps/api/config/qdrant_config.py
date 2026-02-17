"""Qdrant configuration for Legal RAG system.

Optimized settings for production deployment with 1.2M+ legal documents.
"""

import os
from typing import Any


# ── Collection Configuration ──

LEGAL_COLLECTION_NAME = "belgian_legal_docs"
LEGAL_VECTOR_DIM = 1536  # text-embedding-3-large

# Document collection (for case documents)
DOCUMENT_COLLECTION_NAME = "lexibel_documents"
DOCUMENT_VECTOR_DIM = 384  # all-MiniLM-L6-v2


# ── HNSW Index Parameters ──

HNSW_CONFIG = {
    "m": 16,  # Number of edges per node (connectivity)
    "ef_construct": 100,  # Build quality (higher = better quality, slower build)
}

HNSW_SEARCH_PARAMS = {
    "ef": 128,  # Search quality (higher = better quality, slower search)
}


# ── Quantization (for large-scale deployment) ──

ENABLE_QUANTIZATION = os.getenv("ENABLE_QUANTIZATION", "false").lower() == "true"

QUANTIZATION_CONFIG = {
    "type": "scalar",  # or "product" for larger datasets
    "quantile": 0.99,
    "always_ram": True,
}


# ── Chunking Strategy ──

CHUNK_CONFIG = {
    "chunk_size": 500,  # tokens
    "chunk_overlap": 100,  # tokens
    "min_chunk_size": 50,  # minimum viable chunk
}


# ── Search Configuration ──

SEARCH_CONFIG = {
    "default_limit": 10,
    "max_limit": 50,
    "vector_weight": 0.7,  # Hybrid search: 70% semantic
    "keyword_weight": 0.3,  # 30% keyword
    "enable_reranking": True,
    "reranking_top_k": 20,  # Re-rank top 20 results
}


# ── Re-ranking Models ──

RERANKING_MODELS = {
    "default": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "multilingual": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
    "legal": "cross-encoder/ms-marco-MiniLM-L-6-v2",  # TODO: Fine-tune on legal data
}


# ── Qdrant Client Configuration ──

def get_qdrant_config() -> dict[str, Any]:
    """Get Qdrant client configuration from environment."""
    return {
        "url": os.getenv("QDRANT_URL", "http://localhost:6333"),
        "api_key": os.getenv("QDRANT_API_KEY"),
        "timeout": 30.0,  # seconds
        "prefer_grpc": False,  # Use HTTP for simplicity
    }


# ── Collection Schema ──

LEGAL_COLLECTION_SCHEMA = {
    "vectors": {
        "size": LEGAL_VECTOR_DIM,
        "distance": "Cosine",
    },
    "hnsw_config": HNSW_CONFIG,
    "optimizers_config": {
        "default_segment_number": 2,
        "max_segment_size": 200000,
        "memmap_threshold": 50000,
        "indexing_threshold": 20000,
    },
}


# ── Payload Schema (for filtering) ──

LEGAL_PAYLOAD_SCHEMA = {
    "tenant_id": "keyword",  # indexed for filtering
    "document_type": "keyword",  # code_civil, jurisprudence, etc.
    "jurisdiction": "keyword",  # federal, wallonie, etc.
    "article_number": "keyword",  # nullable
    "date_published": "datetime",  # nullable
}


# ── Performance Tuning ──

PERFORMANCE_CONFIG = {
    # Batch settings
    "batch_size": 100,  # documents per batch
    "parallel_uploads": 4,  # concurrent upload threads

    # Cache settings
    "cache_enabled": True,
    "cache_size": 100,  # queries
    "cache_ttl": 3600,  # seconds (1 hour)

    # Memory settings
    "max_memory_mb": 4096,  # 4GB for vector index
    "mmap_threshold": 50000,  # use memory mapping above this
}


# ── Data Sources ──

LEGAL_DATA_SOURCES = {
    "code_civil": {
        "name": "Code Civil Belge",
        "priority": 1,  # Higher priority in search results
        "update_frequency": "monthly",
    },
    "code_judiciaire": {
        "name": "Code Judiciaire",
        "priority": 1,
        "update_frequency": "monthly",
    },
    "code_penal": {
        "name": "Code Pénal",
        "priority": 1,
        "update_frequency": "monthly",
    },
    "moniteur_belge": {
        "name": "Moniteur Belge",
        "priority": 2,
        "update_frequency": "daily",
    },
    "cour_cassation": {
        "name": "Cour de Cassation",
        "priority": 2,
        "update_frequency": "weekly",
    },
    "jurisprudence": {
        "name": "Jurisprudence",
        "priority": 2,
        "update_frequency": "weekly",
    },
    "eu_directive": {
        "name": "Directives UE",
        "priority": 3,
        "update_frequency": "monthly",
    },
}


# ── Monitoring ──

MONITORING_CONFIG = {
    "log_queries": True,
    "log_slow_queries_ms": 1000,  # Log queries slower than 1s
    "track_metrics": True,
    "metrics_interval": 60,  # seconds
}


# ── Export Configuration ──

def export_config() -> dict[str, Any]:
    """Export all configuration as dictionary."""
    return {
        "collections": {
            "legal": {
                "name": LEGAL_COLLECTION_NAME,
                "vector_dim": LEGAL_VECTOR_DIM,
                "schema": LEGAL_COLLECTION_SCHEMA,
            },
            "documents": {
                "name": DOCUMENT_COLLECTION_NAME,
                "vector_dim": DOCUMENT_VECTOR_DIM,
            },
        },
        "hnsw": HNSW_CONFIG,
        "search": SEARCH_CONFIG,
        "chunking": CHUNK_CONFIG,
        "performance": PERFORMANCE_CONFIG,
        "monitoring": MONITORING_CONFIG,
    }
