"""Chunking service — split documents into indexable fragments.

Supports PDF (pdfplumber), DOCX (python-docx), and plain text.
Sliding window: max 512 tokens, 64 token overlap.
"""

import io
import uuid
from dataclasses import dataclass, field
from typing import Optional

import tiktoken


@dataclass
class Chunk:
    """A text fragment with metadata for vector indexing."""

    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    chunk_index: int = 0
    page_number: Optional[int] = None
    case_id: Optional[str] = None
    document_id: Optional[str] = None
    evidence_link_id: Optional[str] = None
    tenant_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)


# Token limits
MAX_TOKENS = 512
OVERLAP_TOKENS = 64

# Lazy-loaded encoder
_encoder: Optional[tiktoken.Encoding] = None


def _get_encoder() -> tiktoken.Encoding:
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken cl100k_base."""
    return len(_get_encoder().encode(text))


def _split_text_into_chunks(
    text: str,
    max_tokens: int = MAX_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[str]:
    """Split text into overlapping token windows."""
    enc = _get_encoder()
    tokens = enc.encode(text)

    if len(tokens) <= max_tokens:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))
        if end >= len(tokens):
            break
        start += max_tokens - overlap_tokens

    return chunks


def extract_text_from_pdf(content: bytes) -> list[tuple[str, int]]:
    """Extract text per page from PDF bytes. Returns [(text, page_num), ...]."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber is required for PDF processing")

    pages: list[tuple[str, int]] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append((text, i + 1))
    return pages


def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX bytes."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx is required for DOCX processing")

    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def chunk_text(
    text: str,
    case_id: Optional[str] = None,
    document_id: Optional[str] = None,
    evidence_link_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    page_number: Optional[int] = None,
    extra_metadata: Optional[dict] = None,
) -> list[Chunk]:
    """Chunk plain text into fragments with metadata."""
    raw_chunks = _split_text_into_chunks(text)
    chunks: list[Chunk] = []
    for idx, content in enumerate(raw_chunks):
        chunks.append(
            Chunk(
                content=content,
                chunk_index=idx,
                page_number=page_number,
                case_id=case_id,
                document_id=document_id,
                evidence_link_id=evidence_link_id,
                tenant_id=tenant_id,
                metadata=extra_metadata or {},
            )
        )
    return chunks


def chunk_document(
    content: bytes,
    mime_type: str,
    case_id: Optional[str] = None,
    document_id: Optional[str] = None,
    evidence_link_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> list[Chunk]:
    """Chunk a document (PDF, DOCX, or text) into fragments."""
    if mime_type == "application/pdf":
        pages = extract_text_from_pdf(content)
        all_chunks: list[Chunk] = []
        global_idx = 0
        for text, page_num in pages:
            page_chunks = chunk_text(
                text,
                case_id=case_id,
                document_id=document_id,
                evidence_link_id=evidence_link_id,
                tenant_id=tenant_id,
                page_number=page_num,
            )
            for c in page_chunks:
                c.chunk_index = global_idx
                global_idx += 1
            all_chunks.extend(page_chunks)
        return all_chunks

    elif mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        text = extract_text_from_docx(content)
        return chunk_text(
            text,
            case_id=case_id,
            document_id=document_id,
            evidence_link_id=evidence_link_id,
            tenant_id=tenant_id,
        )

    else:
        # Plain text fallback
        text = content.decode("utf-8", errors="replace")
        return chunk_text(
            text,
            case_id=case_id,
            document_id=document_id,
            evidence_link_id=evidence_link_id,
            tenant_id=tenant_id,
        )


# ── Embedding generation ──


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using sentence-transformers all-MiniLM-L6-v2.

    Returns list of 384-dimensional vectors.
    Falls back to random vectors if sentence-transformers not available.
    """
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(texts, show_progress_bar=False)
        return [e.tolist() for e in embeddings]
    except ImportError:
        # Stub: deterministic pseudo-embeddings for testing
        import hashlib

        result: list[list[float]] = []
        for text in texts:
            h = hashlib.sha256(text.encode()).digest()
            vec = [((b % 200) - 100) / 100.0 for b in h[:48]]
            # Pad to 384 dims
            vec = (vec * 8)[:384]
            result.append(vec)
        return result
