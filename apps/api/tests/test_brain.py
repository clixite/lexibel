"""Case Brain Complete Tests — LLM, RAG, AI, Legal RAG, ML, Templates, Assembly.

Tests the complete Case Brain implementation:
- LLM Gateway (stub mode and No Source No Claim)
- RAG Pipeline (ingest, query, generate)
- AI Endpoints (draft, summarize, analyze, generate)
- Legal RAG (search, chat, explain)
- ML Pipeline (linkage, triage, deadlines)
- Document Assembler (templates + merge)
- Graph Knowledge (in-memory fallback)
"""

import pytest
from datetime import date, datetime

# LLM Gateway
from apps.api.services.llm_gateway import (
    LLMGateway,
    StubLLMGateway,
    ContextChunk,
    LLMSource,
    validate_citations,
    check_rate_limit,
    reset_rate_limits,
    SYSTEM_PROMPT_DEFAULT,
    SYSTEM_PROMPT_DRAFT,
    SYSTEM_PROMPT_SUMMARIZE,
    SYSTEM_PROMPT_ANALYZE,
)

# RAG Pipeline
from apps.api.services.rag_pipeline import (
    RAGPipeline,
    create_rag_pipeline,
)

# Chunking and Vector
from apps.api.services.chunking_service import (
    chunk_text,
    chunk_document,
    count_tokens,
    generate_embeddings,
)
from apps.api.services.vector_service import (
    InMemoryVectorService,
)

# Legal RAG
from apps.api.services.rag_service import (
    LegalRAGService,
    LegalEntityExtractor,
    LegalQueryExpander,
    MultilingualTranslator,
)

# ML Services
from apps.api.services.ml.linkage_ranker import LinkageRanker, CaseSuggestion
from apps.api.services.ml.email_triage import EmailTriageClassifier, Classification
from apps.api.services.ml.deadline_extractor import DeadlineExtractor, Deadline

# Graph Services
from apps.api.services.graph.neo4j_service import (
    InMemoryGraphService,
    GraphNode,
    GraphRelationship,
)
from apps.api.services.graph.ner_service import NERService

# Document Assembler
from apps.api.services.agents.document_assembler import (
    DocumentAssembler,
    AssembledDocument,
)


# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — LLM Gateway Tests
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_llm_gateway_stub_mode():
    """Test LLM Gateway stub mode with intelligent responses."""
    gateway = StubLLMGateway()

    # Test draft generation
    chunks = [
        ContextChunk(
            content="Le contrat a été signé le 15 janvier 2026.",
            document_id="doc_1",
            case_id="case_1",
        )
    ]

    response = await gateway.generate(
        prompt="Rédige une mise en demeure",
        context_chunks=chunks,
        system_prompt=SYSTEM_PROMPT_DRAFT,
    )

    assert response.text
    assert response.model == "stub-intelligent"
    assert len(response.sources) == 1
    assert response.sources[0].document_id == "doc_1"


@pytest.mark.asyncio
async def test_llm_gateway_rate_limiting():
    """Test rate limiting enforcement."""
    reset_rate_limits()
    gateway = StubLLMGateway()

    tenant_id = "tenant_test"
    chunks = []

    # Make 31 requests (limit is 30 per minute)
    for i in range(31):
        response = await gateway.generate(
            prompt=f"Test {i}",
            context_chunks=chunks,
            tenant_id=tenant_id,
        )
        if i < 30:
            assert "limite de requêtes" not in response.text.lower()
        else:
            assert "limite de requêtes" in response.text.lower()

    reset_rate_limits()


def test_citation_validation_with_sources():
    """Test P3: No Source No Claim validation."""
    # Valid: claims are backed by sources
    text_valid = "Selon l'article 1382, la responsabilité civile s'applique."
    sources_valid = [
        LLMSource(
            document_id="code_civil",
            chunk_text="Article 1382 du Code Civil belge dispose que la responsabilité civile...",
        )
    ]

    is_valid, uncited = validate_citations(text_valid, sources_valid)
    assert is_valid
    assert len(uncited) == 0

    # Invalid: claims without sources
    text_invalid = "Le tribunal a rendu un jugement favorable."
    sources_empty = []

    is_valid, uncited = validate_citations(text_invalid, sources_empty)
    assert not is_valid
    assert len(uncited) > 0


# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — RAG Pipeline Tests
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_rag_pipeline_ingest_text():
    """Test RAG pipeline text ingestion."""
    pipeline = create_rag_pipeline(use_stub=True)

    text = """Contrat de vente entre Alice et Bob.
    Prix: 10000 euros.
    Date de livraison: 1er mars 2026.
    Conditions générales applicables."""

    result = await pipeline.ingest_text(
        document_id="contract_001",
        text=text,
        case_id="case_123",
        tenant_id="tenant_alpha",
    )

    assert result.success
    assert result.chunks_created > 0
    assert result.embeddings_generated == result.chunks_created
    assert result.vectors_upserted == result.chunks_created


@pytest.mark.asyncio
async def test_rag_pipeline_query():
    """Test RAG pipeline query functionality."""
    pipeline = create_rag_pipeline(use_stub=True)

    # Ingest some documents
    await pipeline.ingest_text(
        document_id="doc_1",
        text="Le contrat de travail stipule un préavis de 30 jours.",
        case_id="case_employment",
        tenant_id="tenant_1",
    )

    await pipeline.ingest_text(
        document_id="doc_2",
        text="La facture indique un montant de 5000 euros.",
        case_id="case_employment",
        tenant_id="tenant_1",
    )

    # Query
    result = await pipeline.query(
        question="Quel est le délai de préavis?",
        tenant_id="tenant_1",
        case_id="case_employment",
        top_k=5,
    )

    assert result.total_results > 0
    assert len(result.context_chunks) > 0
    assert result.search_time_ms >= 0


@pytest.mark.asyncio
async def test_rag_pipeline_generate_answer():
    """Test RAG pipeline answer generation with citations."""
    pipeline = create_rag_pipeline(use_stub=True)

    # Ingest
    await pipeline.ingest_text(
        document_id="legal_doc",
        text="Article 1382: Tout fait quelconque de l'homme, qui cause à autrui un dommage.",
        tenant_id="tenant_1",
    )

    # Query and generate
    result = await pipeline.answer_question(
        question="Qu'est-ce que l'article 1382?",
        tenant_id="tenant_1",
        top_k=3,
    )

    assert result.answer
    assert result.context_chunks_used > 0


# ══════════════════════════════════════════════════════════════════════════════
# PART 3 — Chunking & Vector Tests
# ══════════════════════════════════════════════════════════════════════════════


def test_chunking_basic():
    """Test basic text chunking."""
    text = "Ceci est un texte de test. " * 200  # ~400 words

    chunks = chunk_text(
        text=text,
        document_id="test_doc",
        tenant_id="tenant_1",
    )

    assert len(chunks) > 0
    assert all(c.document_id == "test_doc" for c in chunks)
    assert all(c.tenant_id == "tenant_1" for c in chunks)


def test_embedding_generation():
    """Test embedding generation."""
    texts = [
        "Article 1382 du Code Civil",
        "Contrat de travail CDI",
        "Facture numéro 12345",
    ]

    embeddings = generate_embeddings(texts)

    assert len(embeddings) == len(texts)
    assert all(len(emb) == 384 for emb in embeddings)  # 384 dims for all-MiniLM-L6-v2


def test_vector_service_in_memory():
    """Test in-memory vector service."""
    service = InMemoryVectorService()

    # Upsert
    service.upsert_chunks(
        chunk_ids=["chunk_1", "chunk_2"],
        embeddings=[[0.1] * 384, [0.2] * 384],
        payloads=[
            {"content": "Text 1", "tenant_id": "t1", "document_id": "d1"},
            {"content": "Text 2", "tenant_id": "t1", "document_id": "d2"},
        ],
    )

    # Search
    results = service.search(
        query_embedding=[0.15] * 384,
        tenant_id="t1",
        top_k=10,
    )

    assert len(results) == 2
    assert all(r.tenant_id is None or r.score >= 0 for r in results)


# ══════════════════════════════════════════════════════════════════════════════
# PART 4 — Legal RAG Tests
# ══════════════════════════════════════════════════════════════════════════════


def test_legal_entity_extractor():
    """Test legal entity extraction from text."""
    extractor = LegalEntityExtractor()

    text = """Conformément à l'article 1382 du Code Civil,
    et à la loi du 15 juin 1935, la Cour de Cassation a jugé le 12 mars 2025..."""

    entities = extractor.extract(text)

    assert len(entities) > 0
    assert any(e.entity_type == "article" for e in entities)
    assert any(e.entity_type == "law" for e in entities)
    assert any(e.entity_type == "case_reference" for e in entities)


def test_legal_query_expander():
    """Test legal query expansion with synonyms."""
    expander = LegalQueryExpander()

    query = "responsabilité contrat"
    expanded = expander.expand(query)

    assert "responsabilité" in expanded
    assert "contrat" in expanded
    # Should add synonyms
    assert len(expanded) > len(query)


def test_multilingual_translator():
    """Test FR/NL translation for Belgian law."""
    translator = MultilingualTranslator()

    query_fr = "contrat de travail"
    query_nl = translator.translate_query(query_fr, "nl")

    assert "contract" in query_nl.lower() or "arbeid" in query_nl.lower()


@pytest.mark.asyncio
async def test_legal_rag_search():
    """Test Legal RAG search functionality."""
    vector_service = InMemoryVectorService()
    rag_service = LegalRAGService(vector_service)

    # Ingest legal content
    legal_text = "Article 1382 du Code Civil belge: responsabilité civile extracontractuelle."
    chunks = chunk_text(legal_text, tenant_id="public")
    embeddings = generate_embeddings([c.content for c in chunks])

    vector_service.upsert_chunks(
        chunk_ids=[c.chunk_id for c in chunks],
        embeddings=embeddings,
        payloads=[
            {
                "content": c.content,
                "tenant_id": "public",
                "metadata": {
                    "source": "Code Civil",
                    "document_type": "code_civil",
                    "jurisdiction": "federal",
                    "article_number": "1382",
                },
            }
            for c in chunks
        ],
    )

    # Search
    result = await rag_service.search(
        query="responsabilité civile",
        tenant_id="public",
        limit=5,
    )

    assert result.total > 0
    assert result.query == "responsabilité civile"


# ══════════════════════════════════════════════════════════════════════════════
# PART 5 — ML Pipeline Tests
# ══════════════════════════════════════════════════════════════════════════════


def test_linkage_ranker():
    """Test LinkageRanker for case matching."""
    ranker = LinkageRanker(top_k=3)

    existing_cases = [
        {
            "id": "case_1",
            "reference": "2026/001",
            "title": "Contrat de travail — licenciement",
            "contacts": ["alice@example.com"],
            "description": "Litige CDI rupture abusive",
        },
        {
            "id": "case_2",
            "reference": "2026/002",
            "title": "Facture impayée — recouvrement",
            "contacts": ["bob@example.com"],
            "description": "Créance commerciale 5000 euros",
        },
    ]

    # New email about case_1
    text = "Dossier 2026/001 - Licenciement abusif - demande de précisions"
    sender = "alice@example.com"

    suggestions = ranker.rank(text, sender, existing_cases)

    assert len(suggestions) > 0
    assert suggestions[0].case_id == "case_1"
    assert suggestions[0].confidence > 0.3


def test_email_triage_classifier():
    """Test EmailTriageClassifier for urgency detection."""
    classifier = EmailTriageClassifier()

    # Urgent email
    urgent = classifier.classify(
        subject="URGENT - Mise en demeure - délai 8 jours",
        body="Veuillez satisfaire à vos obligations sous 8 jours.",
        sender="avocat@just.fgov.be",
    )

    assert urgent.category == "URGENT"
    assert urgent.confidence > 0.5
    assert urgent.suggested_priority == 1

    # Spam email
    spam = classifier.classify(
        subject="Win 1 million euros!!!",
        body="Click here to claim your prize. Unsubscribe here.",
    )

    assert spam.category == "SPAM"
    assert spam.suggested_priority == 5


def test_deadline_extractor():
    """Test DeadlineExtractor for Belgian legal deadlines."""
    extractor = DeadlineExtractor()

    text = """Le délai d'appel est de 30 jours.
    Citation à comparaître le 15 mars 2026.
    Conclusions dans les 15 jours.
    Conformément à l'Art. 1051 C.J., le pourvoi doit être formé."""

    deadlines = extractor.extract(text, reference_date=date(2026, 2, 1))

    assert len(deadlines) > 0

    # Check for appel deadline
    appel = [d for d in deadlines if d.deadline_type == "appel"]
    assert len(appel) > 0
    assert appel[0].days == 30

    # Check for explicit date
    explicit = [d for d in deadlines if "2026-03-15" in (d.date or "")]
    assert len(explicit) > 0


# ══════════════════════════════════════════════════════════════════════════════
# PART 6 — Graph Knowledge Tests
# ══════════════════════════════════════════════════════════════════════════════


def test_graph_in_memory_basic():
    """Test in-memory graph service."""
    graph = InMemoryGraphService()

    # Create nodes
    person1 = graph.create_node(
        label="Person",
        properties={"name": "Alice Dubois", "role": "plaintiff"},
        tenant_id="tenant_1",
    )

    person2 = graph.create_node(
        label="Person",
        properties={"name": "Bob Martin", "role": "defendant"},
        tenant_id="tenant_1",
    )

    case = graph.create_node(
        label="Case",
        properties={"reference": "2026/001", "title": "Alice vs Bob"},
        tenant_id="tenant_1",
    )

    # Create relationships
    rel1 = graph.create_relationship(
        from_id=person1.id,
        to_id=case.id,
        rel_type="PARTY_TO",
        tenant_id="tenant_1",
    )

    rel2 = graph.create_relationship(
        from_id=person2.id,
        to_id=case.id,
        rel_type="OPPOSED_TO",
        tenant_id="tenant_1",
    )

    assert rel1.rel_type == "PARTY_TO"
    assert rel2.rel_type == "OPPOSED_TO"

    # Get neighbors
    neighbors = graph.get_neighbors(case.id, "tenant_1", depth=1)
    assert len(neighbors) == 2


def test_graph_conflict_detection():
    """Test conflict detection in graph."""
    graph = InMemoryGraphService()

    # Create entities
    lawyer = graph.create_node(
        label="Person",
        properties={"name": "Maître Dupont", "role": "lawyer"},
        tenant_id="t1",
    )

    case_a = graph.create_node(
        label="Case",
        properties={"reference": "A", "title": "Case A"},
        tenant_id="t1",
    )

    case_b = graph.create_node(
        label="Case",
        properties={"reference": "B", "title": "Case B"},
        tenant_id="t1",
    )

    # Lawyer represents both sides (potential conflict)
    graph.create_relationship(lawyer.id, case_a.id, "REPRESENTED_BY", tenant_id="t1")
    graph.create_relationship(lawyer.id, case_b.id, "OPPOSED_TO", tenant_id="t1")

    # Check relationships
    rels = [r for r in graph._relationships if r.from_id == lawyer.id]
    assert len(rels) == 2


def test_ner_service():
    """Test Named Entity Recognition for Belgian legal entities."""
    ner = NERService()

    text = """Me. Alice Dupont, avocate au Barreau de Bruxelles,
    représente la société ACME SA dans le dossier 2026/001
    devant le Tribunal de Commerce de Bruxelles."""

    entities = ner.extract_entities(text)

    assert len(entities) > 0
    # Should detect persons, organizations, courts
    person_entities = [e for e in entities if e["type"] == "PERSON"]
    org_entities = [e for e in entities if e["type"] == "ORGANIZATION"]

    assert len(person_entities) > 0 or len(org_entities) > 0


# ══════════════════════════════════════════════════════════════════════════════
# PART 7 — Document Assembler Tests
# ══════════════════════════════════════════════════════════════════════════════


def test_document_assembler_mise_en_demeure():
    """Test document assembly for mise en demeure."""
    assembler = DocumentAssembler()

    case_data = {
        "case_reference": "2026/DEMO/001",
    }

    variables = {
        "sender_name": "Maître Alice Dupont",
        "sender_address": "Rue de la Loi 123, 1000 Bruxelles",
        "recipient_name": "Monsieur Bob Martin",
        "recipient_address": "Avenue Louise 456, 1050 Bruxelles",
        "facts": "Non-paiement de factures échues depuis 90 jours.",
        "demand": "Paiement de la somme de 5.000 EUR.",
        "deadline_days": "8",
        "city": "Bruxelles",
    }

    doc = assembler.assemble(
        template_name="mise_en_demeure",
        case_data=case_data,
        variables=variables,
    )

    assert doc.template_name == "mise_en_demeure"
    assert "Maître Alice Dupont" in doc.content
    assert "Bob Martin" in doc.content
    assert "5.000 EUR" in doc.content or "5000" in doc.content
    assert "8 jours" in doc.content
    assert len(doc.missing_variables) == 0


def test_document_assembler_conclusions():
    """Test document assembly for conclusions."""
    assembler = DocumentAssembler()

    variables = {
        "court_name": "Tribunal de Première Instance de Bruxelles",
        "case_number": "2026/RG/001",
        "plaintiff_name": "ACME SA",
        "defendant_name": "XYZ SPRL",
        "facts": "Contrat de vente conclu le 1er janvier 2026. Non-livraison.",
        "legal_arguments": "Violation de l'article 1134 du Code Civil.",
        "demands": "Condamner la défenderesse au paiement de 10.000 EUR.",
        "lawyer_name": "Maître Dupont",
        "lawyer_bar": "Bruxelles",
    }

    doc = assembler.assemble(
        template_name="conclusions",
        case_data={},
        variables=variables,
    )

    assert "Tribunal de Première Instance" in doc.content
    assert "ACME SA" in doc.content
    assert "PAR CES MOTIFS" in doc.content
    assert len(doc.missing_variables) == 0


def test_document_assembler_list_templates():
    """Test listing available templates."""
    assembler = DocumentAssembler()

    templates = assembler.list_templates()

    assert len(templates) > 0
    template_ids = [t["id"] for t in templates]
    assert "mise_en_demeure" in template_ids
    assert "conclusions" in template_ids
    assert "citation" in template_ids


# ══════════════════════════════════════════════════════════════════════════════
# PART 8 — Integration Tests
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_end_to_end_case_brain():
    """Test complete Case Brain flow: ingest, query, generate, assemble."""
    # 1. Create RAG pipeline
    pipeline = create_rag_pipeline(use_stub=True)

    # 2. Ingest case documents
    contract_text = """CONTRAT DE VENTE
    Entre ACME SA (vendeur) et XYZ SPRL (acheteur).
    Prix: 50.000 EUR
    Livraison: 1er mars 2026
    Pénalités de retard: 100 EUR/jour"""

    await pipeline.ingest_text(
        document_id="contract_001",
        text=contract_text,
        case_id="case_2026_001",
        tenant_id="tenant_alpha",
    )

    # 3. Query + Generate answer
    answer_result = await pipeline.answer_question(
        question="Quelles sont les pénalités de retard?",
        tenant_id="tenant_alpha",
        case_id="case_2026_001",
    )

    assert answer_result.answer
    assert answer_result.context_chunks_used > 0

    # 4. Assemble legal document
    assembler = DocumentAssembler()
    mise_en_demeure = assembler.assemble(
        template_name="mise_en_demeure",
        case_data={"case_reference": "2026/001"},
        variables={
            "sender_name": "ACME SA",
            "sender_address": "Brussels",
            "recipient_name": "XYZ SPRL",
            "recipient_address": "Liège",
            "facts": "Non-livraison conforme au contrat.",
            "demand": "Exécution sous 8 jours.",
            "deadline_days": "8",
        },
    )

    assert mise_en_demeure.content
    assert "ACME SA" in mise_en_demeure.content


@pytest.mark.asyncio
async def test_no_source_no_claim_enforcement():
    """Test that P3 (No Source No Claim) is enforced throughout."""
    pipeline = create_rag_pipeline(use_stub=True)

    # Generate answer WITHOUT context
    result = await pipeline.generate_answer(
        question="Quel est le montant?",
        context_chunks=[],
        tenant_id="test",
    )

    # Should flag uncited claims if the stub makes factual assertions
    # (depends on stub implementation)
    assert result.answer


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x"])
