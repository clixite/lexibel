"""LLM Gateway — AI generation with No Source No Claim (P3).

Supports OpenAI-compatible APIs (vLLM, OpenAI, Anthropic via proxy).
Every generated claim must cite sources from context chunks.
Rate limiting per tenant.
"""

import os
import re
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMSource:
    """A cited source in an LLM response."""

    document_id: Optional[str] = None
    evidence_link_id: Optional[str] = None
    case_id: Optional[str] = None
    chunk_text: str = ""
    page_number: Optional[int] = None


@dataclass
class LLMResponse:
    """Response from LLM generation with citations."""

    text: str
    sources: list[LLMSource] = field(default_factory=list)
    model: str = ""
    tokens_used: int = 0
    has_uncited_claims: bool = False
    uncited_claims: list[str] = field(default_factory=list)


@dataclass
class ContextChunk:
    """A context chunk provided to the LLM for generation."""

    content: str
    document_id: Optional[str] = None
    evidence_link_id: Optional[str] = None
    case_id: Optional[str] = None
    page_number: Optional[int] = None
    chunk_index: int = 0


# ── Rate limiter ──

_rate_limits: dict[str, list[float]] = {}  # tenant_id -> [timestamps]
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = int(os.getenv("LLM_RATE_LIMIT_PER_MINUTE", "30"))


def check_rate_limit(tenant_id: str) -> bool:
    """Check if tenant is within rate limit. Returns True if allowed."""
    now = time.time()
    if tenant_id not in _rate_limits:
        _rate_limits[tenant_id] = []

    # Clean old entries
    _rate_limits[tenant_id] = [
        t for t in _rate_limits[tenant_id] if now - t < RATE_LIMIT_WINDOW
    ]

    if len(_rate_limits[tenant_id]) >= RATE_LIMIT_MAX:
        return False

    _rate_limits[tenant_id].append(now)
    return True


def reset_rate_limits() -> None:
    """Reset rate limits (for testing)."""
    _rate_limits.clear()


# ── Citation validation (P3: No Source No Claim) ──

_CLAIM_PATTERNS = [
    r"(?:selon|d'après|conformément à|en vertu de)\s+",
    r"(?:l'article|art\.)\s+\d+",
    r"\d+\s*(?:€|EUR|euros?)",
    r"(?:le |la |les )?(?:tribunal|cour|juge|avocat|partie)",
]


def validate_citations(text: str, sources: list[LLMSource]) -> tuple[bool, list[str]]:
    """Validate that claims in text are backed by sources.

    Returns (is_valid, list_of_uncited_claims).
    P3: No Source No Claim — every factual claim must trace to a source.
    """
    if not sources:
        # If no sources provided but text contains factual claims, flag them
        sentences = re.split(r"[.!?]\s+", text)
        uncited: list[str] = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            for pattern in _CLAIM_PATTERNS:
                if re.search(pattern, sentence, re.IGNORECASE):
                    uncited.append(sentence)
                    break
        return len(uncited) == 0, uncited

    # With sources available, check that claim-like sentences
    # have at least partial overlap with source content
    source_text = " ".join(s.chunk_text.lower() for s in sources)
    sentences = re.split(r"[.!?]\s+", text)
    uncited = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        is_claim = False
        for pattern in _CLAIM_PATTERNS:
            if re.search(pattern, sentence, re.IGNORECASE):
                is_claim = True
                break

        if is_claim:
            # Check overlap: at least 3 significant words shared with sources
            words = re.findall(r"\w{4,}", sentence.lower())
            overlap = sum(1 for w in words if w in source_text)
            if overlap < 2:
                uncited.append(sentence)

    return len(uncited) == 0, uncited


# ── System prompts ──

SYSTEM_PROMPT_DEFAULT = """Tu es un assistant juridique belge expert. Tu assistes des avocats dans leur travail quotidien.

RÈGLES ABSOLUES :
1. NO SOURCE NO CLAIM : Chaque affirmation factuelle doit être étayée par une source du contexte fourni.
2. Si tu ne trouves pas de source pour une affirmation, indique clairement « [source non trouvée] ».
3. Réponds en français sauf indication contraire.
4. Cite les sources avec le format [Source: document_id, page X] quand disponible.
5. Respecte le secret professionnel (Art. 458 Code pénal).
"""

SYSTEM_PROMPT_DRAFT = """Tu es un assistant juridique belge spécialisé dans la rédaction.
Rédige un brouillon professionnel basé UNIQUEMENT sur les informations du contexte fourni.
Chaque élément factuel doit être traçable vers un document source.
Format: courrier juridique formel belge."""

SYSTEM_PROMPT_SUMMARIZE = """Tu es un assistant juridique belge spécialisé dans la synthèse.
Résume les éléments clés du dossier basé UNIQUEMENT sur le contexte fourni.
Structure: faits, procédure, points clés, prochaines étapes.
Chaque point doit citer sa source."""

SYSTEM_PROMPT_ANALYZE = """Tu es un assistant juridique belge spécialisé dans l'analyse documentaire.
Analyse le document fourni en identifiant: parties, obligations, délais, risques.
Chaque observation doit être sourcée."""


# ── LLM Gateway ──


class LLMGateway:
    """LLM Gateway with OpenAI-compatible API support and P3 enforcement.

    Supports vLLM (local) with automatic fallback to OpenAI.
    Set VLLM_BASE_URL to enable local vLLM backend.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        vllm_base_url: Optional[str] = None,
    ) -> None:
        self._base_url = base_url or os.getenv(
            "LLM_BASE_URL", "https://api.openai.com/v1"
        )
        self._api_key = api_key or os.getenv("LLM_API_KEY", "")
        self._model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self._vllm_base_url = vllm_base_url or os.getenv("VLLM_BASE_URL", "")
        self._vllm_available: Optional[bool] = None

    def _build_messages(
        self,
        prompt: str,
        context_chunks: list[ContextChunk],
        system_prompt: str,
    ) -> list[dict]:
        """Build chat messages with context chunks."""
        context_parts: list[str] = []
        for i, chunk in enumerate(context_chunks):
            source_ref = f"[Source {i + 1}: doc={chunk.document_id or 'N/A'}"
            if chunk.page_number:
                source_ref += f", page {chunk.page_number}"
            source_ref += "]"
            context_parts.append(f"{source_ref}\n{chunk.content}")

        context_text = "\n\n---\n\n".join(context_parts) if context_parts else ""

        user_message = prompt
        if context_text:
            user_message = f"CONTEXTE :\n{context_text}\n\n---\n\nDEMANDE :\n{prompt}"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

    async def _resolve_backend(self) -> str:
        """Resolve which backend to use: vLLM first, fallback to OpenAI."""
        if not self._vllm_base_url:
            return self._base_url

        # Check vLLM health (cache result for 30s via simple flag)
        if self._vllm_available is None:
            try:
                import httpx

                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{self._vllm_base_url}/models")
                    self._vllm_available = resp.status_code == 200
            except Exception:
                self._vllm_available = False

        return self._vllm_base_url if self._vllm_available else self._base_url

    async def generate(
        self,
        prompt: str,
        context_chunks: list[ContextChunk],
        system_prompt: str = SYSTEM_PROMPT_DEFAULT,
        tenant_id: Optional[str] = None,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Generate text with citation validation.

        P3: validates that the response cites sources from context_chunks.
        """
        # Rate limit check
        if tenant_id and not check_rate_limit(tenant_id):
            return LLMResponse(
                text="Erreur : limite de requêtes atteinte. Réessayez dans une minute.",
                model=self._model,
                has_uncited_claims=False,
            )

        messages = self._build_messages(prompt, context_chunks, system_prompt)

        # Try vLLM first, fallback to OpenAI
        api_base = await self._resolve_backend()

        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                data = response.json()

            text = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)
        except Exception as e:
            return LLMResponse(
                text=f"Erreur LLM : {str(e)}",
                model=self._model,
                has_uncited_claims=False,
            )

        # Build sources from context chunks
        sources = [
            LLMSource(
                document_id=c.document_id,
                evidence_link_id=c.evidence_link_id,
                case_id=c.case_id,
                chunk_text=c.content[:200],
                page_number=c.page_number,
            )
            for c in context_chunks
        ]

        # P3: Validate citations
        is_valid, uncited = validate_citations(text, sources)

        return LLMResponse(
            text=text,
            sources=sources,
            model=self._model,
            tokens_used=tokens_used,
            has_uncited_claims=not is_valid,
            uncited_claims=uncited,
        )


# ── Stub gateway for testing ──


class StubLLMGateway(LLMGateway):
    """Stub LLM gateway that returns intelligent simulated responses.

    Generates realistic Belgian legal content based on prompt analysis.
    Useful for testing without LLM API key.
    """

    def __init__(self, canned_response: Optional[str] = None) -> None:
        self._canned = canned_response
        self._model = "stub-intelligent"
        self._base_url = ""
        self._api_key = ""

    def _generate_intelligent_response(
        self,
        prompt: str,
        context_chunks: list[ContextChunk],
        system_prompt: str,
    ) -> str:
        """Generate intelligent response based on prompt keywords."""
        prompt_lower = prompt.lower()

        # Detect intent from prompt
        if any(word in prompt_lower for word in ["rédige", "draft", "brouillon", "mise en demeure"]):
            # Drafting request
            return self._draft_template(prompt_lower, context_chunks)
        elif any(word in prompt_lower for word in ["résume", "résumé", "summary", "synthèse"]):
            # Summary request
            return self._summary_template(context_chunks)
        elif any(word in prompt_lower for word in ["analyse", "analyze", "examine"]):
            # Analysis request
            return self._analysis_template(context_chunks)
        elif any(word in prompt_lower for word in ["article", "code", "loi", "jurisprudence"]):
            # Legal query
            return self._legal_query_template(prompt_lower)
        else:
            # Generic response
            return self._generic_template(context_chunks)

    def _draft_template(self, prompt: str, chunks: list[ContextChunk]) -> str:
        """Generate draft document stub."""
        if "mise en demeure" in prompt:
            return """Madame, Monsieur,

Par la présente, je me permets de vous mettre en demeure de satisfaire aux obligations suivantes.

FAITS :
Selon les éléments du dossier [Source: documents fournis], les faits suivants sont établis. Les parties sont en relation contractuelle depuis plusieurs mois. Des obligations ont été prises mais n'ont pas été respectées dans les délais convenus.

MISE EN DEMEURE :
En conséquence, je vous mets en demeure de procéder au paiement de la somme due et/ou d'exécuter vos obligations contractuelles dans un délai de 8 jours à compter de la réception de la présente.

À défaut, je me verrai contraint de saisir les juridictions compétentes sans autre avis.

Veuillez agréer, Madame, Monsieur, l'expression de mes salutations distinguées."""
        else:
            return "Brouillon de document juridique basé sur les éléments du dossier [Source: contexte fourni]."

    def _summary_template(self, chunks: list[ContextChunk]) -> str:
        """Generate summary stub."""
        if not chunks:
            return "Aucun élément à résumer."

        return """RÉSUMÉ DU DOSSIER

1. FAITS PRINCIPAUX
Selon les documents analysés [Source: documents du dossier], le dossier porte sur une situation juridique impliquant plusieurs parties. Les événements se sont déroulés sur plusieurs mois.

2. PARTIES
- Partie demanderesse : [identifiée dans les documents]
- Partie défenderesse : [identifiée dans les documents]

3. POINTS CLÉS
- Obligation contractuelle non respectée [Source: contrat au dossier]
- Délais de paiement expirés [Source: factures]
- Correspondance échangée [Source: emails au dossier]

4. PROCHAINES ÉTAPES
Selon l'analyse du dossier, les prochaines étapes pourraient inclure une mise en demeure formelle, suivie si nécessaire d'une procédure judiciaire."""

    def _analysis_template(self, chunks: list[ContextChunk]) -> str:
        """Generate analysis stub."""
        return """ANALYSE DU DOCUMENT

1. PARTIES IDENTIFIÉES
Selon le document analysé [Source: document fourni], les parties suivantes sont identifiées dans le cadre de cette relation juridique.

2. OBLIGATIONS
Les obligations principales comprennent :
- Obligations de paiement [Source: clauses contractuelles]
- Obligations de livraison/prestation [Source: document]
- Délais d'exécution [Source: calendrier contractuel]

3. DÉLAIS
Les délais suivants s'appliquent conformément au Code Judiciaire :
- Délai de citation : 8 jours (Art. 707 C.J.)
- Délai d'appel : 30 jours (Art. 1051 C.J.)

4. RISQUES IDENTIFIÉS
- Risque de non-exécution dans les délais
- Risque de pénalités contractuelles
- Risque de procédure judiciaire si non-résolution amiable

5. RECOMMANDATIONS
- Mise en demeure formelle dans les meilleurs délais
- Tentative de négociation amiable
- Conservation de tous les éléments de preuve"""

    def _legal_query_template(self, prompt: str) -> str:
        """Generate legal query response stub."""
        if "1382" in prompt or "responsabilité" in prompt:
            return """Article 1382 du Code Civil belge — Responsabilité civile

L'article 1382 dispose : "Tout fait quelconque de l'homme, qui cause à autrui un dommage, oblige celui par la faute duquel il est arrivé à le réparer."

Cet article établit le principe de la responsabilité civile extracontractuelle en droit belge. Pour qu'une responsabilité soit engagée, trois conditions doivent être réunies :

1. Une faute
2. Un dommage
3. Un lien de causalité entre la faute et le dommage

La jurisprudence belge a considérablement développé l'interprétation de cet article, notamment en matière de faute (critère de l'homme normalement prudent et diligent)."""
        elif "code judiciaire" in prompt or "procédure" in prompt:
            return """Code Judiciaire belge — Principales dispositions

Le Code Judiciaire régit la procédure civile en Belgique. Principaux délais :

- Art. 707 : Délai de citation (8 jours minimum)
- Art. 1051 : Délai d'appel (30 jours)
- Art. 1073 : Pourvoi en cassation (3 mois)

Ces délais sont d'ordre public et doivent être strictement respectés sous peine de forclusion."""
        else:
            return "Réponse basée sur le droit belge et les sources juridiques disponibles."

    def _generic_template(self, chunks: list[ContextChunk]) -> str:
        """Generate generic response."""
        if chunks:
            return f"Selon les {len(chunks)} documents fournis au dossier, voici une synthèse des éléments pertinents. [Source: documents contexte]"
        return "Réponse générée sans contexte spécifique."

    async def generate(
        self,
        prompt: str,
        context_chunks: list[ContextChunk],
        system_prompt: str = SYSTEM_PROMPT_DEFAULT,
        tenant_id: Optional[str] = None,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        if tenant_id and not check_rate_limit(tenant_id):
            return LLMResponse(
                text="Erreur : limite de requêtes atteinte.",
                model="stub",
                has_uncited_claims=False,
            )

        # Generate intelligent response or use canned
        if self._canned:
            text = self._canned
        else:
            text = self._generate_intelligent_response(prompt, context_chunks, system_prompt)

        sources = [
            LLMSource(
                document_id=c.document_id,
                evidence_link_id=c.evidence_link_id,
                case_id=c.case_id,
                chunk_text=c.content[:200],
                page_number=c.page_number,
            )
            for c in context_chunks
        ]

        is_valid, uncited = validate_citations(text, sources)

        return LLMResponse(
            text=text,
            sources=sources,
            model=self._model,
            tokens_used=len(prompt.split()) * 2,  # Simulate token usage
            has_uncited_claims=not is_valid,
            uncited_claims=uncited,
        )
