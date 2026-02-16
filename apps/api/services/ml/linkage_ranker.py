"""LinkageRanker — rank which case an incoming event most likely belongs to.

Uses TF-IDF + cosine similarity for text matching, plus contact matching
and reference pattern detection. Upgrade path to fine-tuned model.

Features:
- Subject/body keyword overlap (TF-IDF cosine similarity)
- Contact matching (sender email vs case contacts)
- Recency bias (more recent cases ranked higher)
- Reference pattern detection (dossier numbers, court references)
"""
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CaseSuggestion:
    """A suggested case match with confidence score."""
    case_id: str
    case_reference: str
    case_title: str
    confidence: float  # 0.0 to 1.0
    match_reasons: list[str]


# ── Reference patterns for Belgian legal practice ──

REFERENCE_PATTERNS = [
    re.compile(r"\b(\d{4}/\d{2,4}(?:/[A-Z])?)\b"),           # 2026/001/A
    re.compile(r"\b([Dd]ossier\s+\d+)\b"),                     # Dossier 42
    re.compile(r"\b(RG\s+\d+/\d+(?:/[A-Z])?)\b"),             # RG 2026/123
    re.compile(r"\b(DOS[-\s]?\d{3,6})\b"),                     # DOS-001, DOS 001
    re.compile(r"\b(\d{2}\.\d{2}\.\d{2}\.\d{4})\b"),          # BE court format
]


def _extract_references(text: str) -> list[str]:
    """Extract legal reference patterns from text."""
    refs = []
    for pattern in REFERENCE_PATTERNS:
        refs.extend(pattern.findall(text))
    return [r.strip() for r in refs]


def _tokenize(text: str) -> list[str]:
    """Simple tokenizer: lowercase, split on non-alphanumeric."""
    return re.findall(r"[a-zà-ÿ0-9]+", text.lower())


def _compute_tf(tokens: list[str]) -> dict[str, float]:
    """Compute term frequency."""
    counts = Counter(tokens)
    total = len(tokens) if tokens else 1
    return {term: count / total for term, count in counts.items()}


def _compute_idf(documents: list[list[str]]) -> dict[str, float]:
    """Compute inverse document frequency."""
    n_docs = len(documents)
    if n_docs == 0:
        return {}

    doc_freq: Counter = Counter()
    for doc in documents:
        unique_terms = set(doc)
        for term in unique_terms:
            doc_freq[term] += 1

    return {
        term: math.log((n_docs + 1) / (freq + 1)) + 1
        for term, freq in doc_freq.items()
    }


def _tfidf_vector(tf: dict[str, float], idf: dict[str, float]) -> dict[str, float]:
    """Compute TF-IDF vector."""
    return {term: tf_val * idf.get(term, 1.0) for term, tf_val in tf.items()}


def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Cosine similarity between two sparse vectors."""
    common_terms = set(vec_a.keys()) & set(vec_b.keys())
    if not common_terms:
        return 0.0

    dot = sum(vec_a[t] * vec_b[t] for t in common_terms)
    norm_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    norm_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


class LinkageRanker:
    """Rank existing cases for an incoming event using TF-IDF similarity."""

    def __init__(self, top_k: int = 3) -> None:
        self.top_k = top_k

    def rank(
        self,
        text: str,
        sender: str,
        existing_cases: list[dict],
    ) -> list[CaseSuggestion]:
        """Rank cases by relevance to the incoming event.

        Args:
            text: Combined text from event (subject + body)
            sender: Sender email/name
            existing_cases: List of case dicts with keys:
                id, reference, title, contacts (list of emails),
                description (optional), updated_at (optional)

        Returns:
            Top-K CaseSuggestion sorted by confidence (descending)
        """
        if not existing_cases or not text.strip():
            return []

        event_tokens = _tokenize(text)
        event_refs = _extract_references(text)

        # Build case text representations
        case_docs = []
        for case in existing_cases:
            case_text = f"{case.get('reference', '')} {case.get('title', '')} {case.get('description', '')}"
            case_docs.append(_tokenize(case_text))

        # Add event tokens for IDF computation
        all_docs = case_docs + [event_tokens]
        idf = _compute_idf(all_docs)

        event_tf = _compute_tf(event_tokens)
        event_vec = _tfidf_vector(event_tf, idf)

        suggestions = []

        for i, case in enumerate(existing_cases):
            score = 0.0
            reasons = []

            # 1. TF-IDF cosine similarity (weight: 0.4)
            case_tf = _compute_tf(case_docs[i])
            case_vec = _tfidf_vector(case_tf, idf)
            text_sim = _cosine_similarity(event_vec, case_vec)
            if text_sim > 0.05:
                score += text_sim * 0.4
                reasons.append(f"text_similarity={text_sim:.2f}")

            # 2. Contact matching (weight: 0.25)
            case_contacts = case.get("contacts", [])
            if sender and case_contacts:
                sender_lower = sender.lower()
                for contact in case_contacts:
                    if isinstance(contact, str) and sender_lower in contact.lower():
                        score += 0.25
                        reasons.append(f"contact_match={contact}")
                        break

            # 3. Reference pattern matching (weight: 0.25)
            case_ref = case.get("reference", "")
            if event_refs and case_ref:
                for ref in event_refs:
                    if ref.lower() in case_ref.lower() or case_ref.lower() in ref.lower():
                        score += 0.25
                        reasons.append(f"reference_match={ref}")
                        break

            # 4. Recency bias (weight: 0.1)
            updated_at = case.get("updated_at")
            if updated_at:
                try:
                    if isinstance(updated_at, str):
                        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    else:
                        updated = updated_at
                    days_old = (datetime.now(timezone.utc) - updated).days
                    recency = max(0, 1 - (days_old / 365))  # Linear decay over 1 year
                    score += recency * 0.1
                    if recency > 0.5:
                        reasons.append(f"recent={days_old}d")
                except (ValueError, TypeError):
                    pass

            if score > 0.01:
                suggestions.append(CaseSuggestion(
                    case_id=str(case.get("id", "")),
                    case_reference=case_ref,
                    case_title=case.get("title", ""),
                    confidence=min(score, 1.0),
                    match_reasons=reasons,
                ))

        # Sort by confidence descending, take top K
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions[:self.top_k]
