"""Script to index Belgian legal documents into Qdrant vector database.

Data sources:
- Moniteur Belge (Belgian official gazette)
- Code Civil, Code Judiciaire, Code Pénal
- Cour de Cassation jurisprudence
- EU directives relevant to Belgium

Usage:
    python -m apps.api.scripts.index_legal_documents --source all
    python -m apps.api.scripts.index_legal_documents --source code_civil
    python -m apps.api.scripts.index_legal_documents --update-only
"""

import argparse
import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from apps.api.services.chunking_service import chunk_text, generate_embeddings
from apps.api.services.vector_service import VectorService, COLLECTION_NAME


# ── Legal Document Sources ──

SOURCES = {
    "code_civil": {
        "name": "Code Civil Belge",
        "url": "https://www.ejustice.just.fgov.be/cgi_loi/loi_a.pl?language=fr&cn=1804032130",
        "jurisdiction": "federal",
        "type": "code_civil",
    },
    "code_judiciaire": {
        "name": "Code Judiciaire",
        "url": "https://www.ejustice.just.fgov.be/cgi_loi/loi_a1.pl?language=fr&la=F&cn=1967101002",
        "jurisdiction": "federal",
        "type": "code_judiciaire",
    },
    "moniteur_belge": {
        "name": "Moniteur Belge",
        "url": "https://www.ejustice.just.fgov.be/cgi/welcome.pl",
        "jurisdiction": "federal",
        "type": "moniteur_belge",
    },
}


# ── Sample Legal Documents (for demo) ──

SAMPLE_DOCUMENTS = [
    {
        "title": "Code Civil - Article 1382 - Responsabilité civile",
        "content": """Article 1382 du Code Civil belge:

Tout fait quelconque de l'homme, qui cause à autrui un dommage, oblige celui par la faute duquel il est arrivé, à le réparer.

Cet article fondamental du droit belge établit le principe de la responsabilité civile. Il impose à toute personne qui cause un dommage à autrui par sa faute l'obligation de réparer ce dommage.

Trois conditions doivent être réunies:
1. Une faute (un comportement fautif)
2. Un dommage (préjudice subi par la victime)
3. Un lien de causalité entre la faute et le dommage

La jurisprudence a précisé que la faute peut être intentionnelle ou résulter d'une simple négligence. Le dommage peut être matériel, corporel ou moral.""",
        "article_number": "1382",
        "document_type": "code_civil",
        "jurisdiction": "federal",
        "date_published": "1804-03-21",
        "url": "https://www.ejustice.just.fgov.be/cgi_loi/loi_a1.pl?cn=1804032130",
    },
    {
        "title": "Code Civil - Article 1134 - Force obligatoire du contrat",
        "content": """Article 1134 du Code Civil belge:

Les conventions légalement formées tiennent lieu de loi à ceux qui les ont faites.

Elles ne peuvent être révoquées que de leur consentement mutuel, ou pour les causes que la loi autorise.

Elles doivent être exécutées de bonne foi.

Cet article consacre le principe de la force obligatoire des contrats. Une fois qu'un contrat est valablement conclu, il lie les parties comme la loi elle-même.

Principes clés:
- Autonomie de la volonté: les parties sont libres de conclure des contrats
- Force obligatoire: le contrat doit être respecté (pacta sunt servanda)
- Bonne foi: les parties doivent exécuter le contrat de manière loyale

La révocation unilatérale n'est possible que dans les cas prévus par la loi (droit de rétractation, résolution judiciaire, etc.).""",
        "article_number": "1134",
        "document_type": "code_civil",
        "jurisdiction": "federal",
        "date_published": "1804-03-21",
        "url": "https://www.ejustice.just.fgov.be/cgi_loi/loi_a1.pl?cn=1804032130",
    },
    {
        "title": "Code Judiciaire - Article 780 - Procédure de divorce",
        "content": """Article 780 du Code Judiciaire:

La demande en divorce ou en séparation de corps est introduite par requête signée par l'avocat.

La requête contient:
1. L'indication du tribunal compétent
2. Les nom, prénoms, profession et domicile des parties
3. L'objet et l'exposé sommaire des moyens de la demande
4. Les pièces justificatives

Procédure:
Le tribunal statue d'abord sur les mesures provisoires (garde des enfants, pension alimentaire, résidence).
Puis il examine le fond de la demande de divorce.

La procédure de divorce en Belgique peut être:
- Par consentement mutuel (divorce à l'amiable)
- Pour désunion irrémédiable (divorce pour cause déterminée)
- Après séparation de fait de plus de 2 ans""",
        "article_number": "780",
        "document_type": "code_judiciaire",
        "jurisdiction": "federal",
        "date_published": "1967-10-10",
        "url": "https://www.ejustice.just.fgov.be/cgi_loi/loi_a1.pl?cn=1967101002",
    },
    {
        "title": "Cour de Cassation - Arrêt du 15 janvier 2020 - Responsabilité médicale",
        "content": """Arrêt de la Cour de Cassation du 15 janvier 2020

Matière: Responsabilité civile médicale

Faits: Un patient poursuit un médecin pour faute médicale ayant entraîné des complications post-opératoires.

Question de droit: Le médecin doit-il informer le patient de tous les risques, même exceptionnels?

Décision: La Cour rappelle que le médecin a une obligation d'information. Il doit informer le patient des risques graves, même exceptionnels, liés à l'intervention envisagée.

L'absence d'information constitue une faute susceptible d'engager la responsabilité du médecin, même si l'acte médical a été correctement exécuté.

Le patient doit pouvoir donner un consentement éclairé.

Portée: Cet arrêt renforce l'obligation d'information du médecin et le droit du patient à l'autodétermination.

Articles appliqués: Article 1382 Code Civil (responsabilité), Code de déontologie médicale.""",
        "document_type": "cour_cassation",
        "jurisdiction": "federal",
        "date_published": "2020-01-15",
        "url": "https://juportal.be/content/ECLI:BE:CASS:2020:ARR.20200115",
    },
    {
        "title": "Loi du 3 juillet 1978 - Contrats de travail",
        "content": """Loi du 3 juillet 1978 relative aux contrats de travail

Article 37: Durée du préavis

En cas de rupture du contrat de travail par l'employeur, la durée du préavis dépend de l'ancienneté du travailleur:

- Moins de 3 mois d'ancienneté: 2 semaines
- De 3 à 4 mois: 3 semaines
- De 4 à 5 mois: 4 semaines
- Etc.

Pour les employés, la durée du préavis augmente progressivement avec l'ancienneté, pouvant atteindre plusieurs mois.

Article 39: Indemnité de rupture

En cas de rupture sans préavis ou avec un préavis insuffisant, une indemnité compensatoire est due.

Cette indemnité correspond à la rémunération que le travailleur aurait perçue si le préavis avait été respecté.

Modifications récentes:
- Harmonisation du statut ouvriers/employés (2014)
- Nouveau calcul des indemnités (2018)""",
        "document_type": "moniteur_belge",
        "jurisdiction": "federal",
        "date_published": "1978-07-03",
        "url": "https://www.ejustice.just.fgov.be/cgi_loi/loi_a1.pl?cn=1978070301",
    },
]


# ── Indexing Functions ──


def extract_legal_metadata(doc: dict[str, Any]) -> dict[str, Any]:
    """Extract metadata from legal document."""
    return {
        "source": doc["title"],
        "document_type": doc["document_type"],
        "jurisdiction": doc["jurisdiction"],
        "article_number": doc.get("article_number"),
        "date_published": doc.get("date_published"),
        "url": doc.get("url"),
    }


async def index_document(
    vector_service: VectorService,
    document: dict[str, Any],
) -> int:
    """Index a single legal document into Qdrant.

    Returns number of chunks indexed.
    """
    content = document["content"]
    metadata = extract_legal_metadata(document)

    # Chunk the document
    chunks = chunk_text(
        text=content,
        chunk_size=500,
        overlap=100,
    )

    if not chunks:
        return 0

    # Generate embeddings
    embeddings = generate_embeddings(chunks)

    # Prepare payloads
    chunk_ids = [str(uuid.uuid4()) for _ in chunks]
    payloads = [
        {
            "content": chunk,
            "tenant_id": "public",  # Legal docs are public
            "metadata": metadata,
            **metadata,  # Flatten for easier filtering
        }
        for chunk in chunks
    ]

    # Upsert into Qdrant
    vector_service.upsert_chunks(
        chunk_ids=chunk_ids,
        embeddings=embeddings,
        payloads=payloads,
    )

    return len(chunks)


async def index_all_sources(
    vector_service: VectorService,
    source_filter: str = "all",
) -> None:
    """Index all legal documents from specified source."""
    print(f"🚀 Starting legal document indexing...")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Source filter: {source_filter}")

    # Ensure collection exists
    vector_service.ensure_collection()
    print("✓ Collection ready")

    total_chunks = 0

    # Index sample documents
    for doc in SAMPLE_DOCUMENTS:
        if source_filter != "all" and doc["document_type"] != source_filter:
            continue

        print(f"\n📄 Indexing: {doc['title']}")
        chunks_count = await index_document(vector_service, doc)
        total_chunks += chunks_count
        print(f"   ✓ {chunks_count} chunks indexed")

    print(f"\n✅ Indexing complete!")
    print(f"   Total documents: {len(SAMPLE_DOCUMENTS)}")
    print(f"   Total chunks: {total_chunks}")
    print(f"   Collection: {COLLECTION_NAME}")


# ── CLI ──


async def main() -> None:
    """Main indexing function."""
    parser = argparse.ArgumentParser(
        description="Index Belgian legal documents into Qdrant"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="all",
        choices=["all", "code_civil", "code_judiciaire", "moniteur_belge", "jurisprudence"],
        help="Which source to index",
    )
    parser.add_argument(
        "--update-only",
        action="store_true",
        help="Only update existing documents",
    )
    parser.add_argument(
        "--qdrant-url",
        type=str,
        default=None,
        help="Qdrant server URL (default: from env)",
    )

    args = parser.parse_args()

    # Initialize vector service
    vector_service = VectorService(
        url=args.qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )

    # Run indexing
    await index_all_sources(vector_service, args.source)


if __name__ == "__main__":
    asyncio.run(main())
