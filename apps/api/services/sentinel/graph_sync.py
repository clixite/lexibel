"""SENTINEL graph synchronization service."""

import asyncio
import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import select

from apps.api.services.neo4j_client import get_neo4j_client, Neo4jClient
from packages.db.models.contact import Contact
from packages.db.models.case import Case
from packages.db.models.case_contact import CaseContact
from packages.db.models.user import User
from packages.db.session import get_superadmin_session

logger = logging.getLogger(__name__)


class GraphSyncService:
    """Sync PostgreSQL data to Neo4j graph."""

    def __init__(self):
        self.neo4j_client: Optional[Neo4jClient] = None

    async def initialize(self):
        """Initialize Neo4j client."""
        try:
            self.neo4j_client = await get_neo4j_client()
            logger.info("GraphSyncService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GraphSyncService: {e}")
            raise

    async def sync_person_to_graph(self, person_id: UUID) -> bool:
        """Create or update Person node in Neo4j."""
        try:
            # Get person from PostgreSQL
            async with get_superadmin_session() as session:
                result = await session.execute(
                    select(Contact).where(Contact.id == person_id)
                )
                contact = result.scalar_one_or_none()

                if not contact:
                    logger.warning(f"Contact {person_id} not found")
                    return False

                if contact.type != "natural":
                    logger.warning(f"Contact {person_id} is not a natural person")
                    return False

                # Create MERGE query for Person node
                query = """
                MERGE (p:Person {id: $id})
                SET p.name = $name,
                    p.email = $email,
                    p.phone = $phone,
                    p.language = $language,
                    p.address = $address,
                    p.updated_at = datetime()
                RETURN p
                """

                parameters = {
                    "id": str(contact.id),
                    "name": contact.full_name,
                    "email": contact.email,
                    "phone": contact.phone_e164,
                    "language": contact.language,
                    "address": contact.address if contact.address else None,
                }

                # Execute query
                await self.neo4j_client.execute_query(query, parameters)
                logger.info(f"Synced person {person_id} to Neo4j")
                return True

        except Exception as e:
            logger.error(f"Failed to sync person {person_id}: {e}")
            return False

    async def sync_company_to_graph(self, company_id: UUID) -> bool:
        """Create or update Company node in Neo4j."""
        try:
            # Get company from PostgreSQL
            async with get_superadmin_session() as session:
                result = await session.execute(
                    select(Contact).where(Contact.id == company_id)
                )
                contact = result.scalar_one_or_none()

                if not contact:
                    logger.warning(f"Contact {company_id} not found")
                    return False

                if contact.type != "legal":
                    logger.warning(f"Contact {company_id} is not a legal person")
                    return False

                # Create MERGE query for Company node
                query = """
                MERGE (c:Company {id: $id})
                SET c.name = $name,
                    c.email = $email,
                    c.phone = $phone,
                    c.bce_number = $bce_number,
                    c.address = $address,
                    c.language = $language,
                    c.updated_at = datetime()
                RETURN c
                """

                parameters = {
                    "id": str(contact.id),
                    "name": contact.full_name,
                    "email": contact.email,
                    "phone": contact.phone_e164,
                    "bce_number": contact.bce_number,
                    "address": contact.address if contact.address else None,
                    "language": contact.language,
                }

                # Execute query
                await self.neo4j_client.execute_query(query, parameters)
                logger.info(f"Synced company {company_id} to Neo4j")
                return True

        except Exception as e:
            logger.error(f"Failed to sync company {company_id}: {e}")
            return False

    async def sync_case_to_graph(self, case_id: UUID) -> bool:
        """Create or update Case node in Neo4j."""
        try:
            # Get case from PostgreSQL
            async with get_superadmin_session() as session:
                result = await session.execute(select(Case).where(Case.id == case_id))
                case = result.scalar_one_or_none()

                if not case:
                    logger.warning(f"Case {case_id} not found")
                    return False

                # Create MERGE query for Case node
                query = """
                MERGE (case:Case {id: $id})
                SET case.reference = $reference,
                    case.title = $title,
                    case.matter_type = $matter_type,
                    case.status = $status,
                    case.jurisdiction = $jurisdiction,
                    case.court_reference = $court_reference,
                    case.opened_at = datetime($opened_at),
                    case.closed_at = $closed_at,
                    case.updated_at = datetime()
                RETURN case
                """

                parameters = {
                    "id": str(case.id),
                    "reference": case.reference,
                    "title": case.title,
                    "matter_type": case.matter_type,
                    "status": case.status,
                    "jurisdiction": case.jurisdiction,
                    "court_reference": case.court_reference,
                    "opened_at": case.opened_at.isoformat() if case.opened_at else None,
                    "closed_at": datetime.combine(
                        case.closed_at, datetime.min.time()
                    ).isoformat()
                    if case.closed_at
                    else None,
                }

                # Execute query
                await self.neo4j_client.execute_query(query, parameters)
                logger.info(f"Synced case {case_id} to Neo4j")
                return True

        except Exception as e:
            logger.error(f"Failed to sync case {case_id}: {e}")
            return False

    async def sync_relationships(self, case_id: UUID) -> int:
        """Sync relationships for a case."""
        try:
            relationships_created = 0

            async with get_superadmin_session() as session:
                # Get case data
                case_result = await session.execute(
                    select(Case).where(Case.id == case_id)
                )
                case = case_result.scalar_one_or_none()

                if not case:
                    logger.warning(f"Case {case_id} not found")
                    return 0

                # Get case contacts (clients and adversaries)
                case_contacts_result = await session.execute(
                    select(CaseContact).where(CaseContact.case_id == case_id)
                )
                case_contacts = case_contacts_result.scalars().all()

                # Get responsible user (lawyer)
                user_result = await session.execute(
                    select(User).where(User.id == case.responsible_user_id)
                )
                lawyer = user_result.scalar_one_or_none()

                if not lawyer:
                    logger.warning(
                        f"Lawyer {case.responsible_user_id} not found for case {case_id}"
                    )
                    return 0

                # Create Lawyer node if not exists
                lawyer_query = """
                MERGE (l:Lawyer {id: $id})
                SET l.name = $name,
                    l.email = $email,
                    l.role = $role,
                    l.updated_at = datetime()
                """
                await self.neo4j_client.execute_query(
                    lawyer_query,
                    {
                        "id": str(lawyer.id),
                        "name": lawyer.full_name,
                        "email": lawyer.email,
                        "role": lawyer.role,
                    },
                )

                # Process case contacts and create relationships
                for case_contact in case_contacts:
                    contact_result = await session.execute(
                        select(Contact).where(Contact.id == case_contact.contact_id)
                    )
                    contact = contact_result.scalar_one_or_none()

                    if not contact:
                        continue

                    # Determine node label based on contact type
                    node_label = "Company" if contact.type == "legal" else "Person"

                    # REPRESENTS: Lawyer -> Client
                    if case_contact.role == "client":
                        represents_query = f"""
                        MATCH (l:Lawyer {{id: $lawyer_id}}), (c:{node_label} {{id: $contact_id}})
                        MERGE (l)-[r:REPRESENTS]->(c)
                        SET r.since = datetime($since),
                            r.case_id = $case_id,
                            r.case_reference = $case_reference
                        """
                        await self.neo4j_client.execute_query(
                            represents_query,
                            {
                                "lawyer_id": str(lawyer.id),
                                "contact_id": str(contact.id),
                                "since": case.opened_at.isoformat()
                                if case.opened_at
                                else datetime.now().isoformat(),
                                "case_id": str(case.id),
                                "case_reference": case.reference,
                            },
                        )
                        relationships_created += 1

                    # OPPOSES: Client -> Adversary (need to find clients first)
                    elif case_contact.role == "adverse":
                        # Find all clients for this case
                        clients_result = await session.execute(
                            select(CaseContact).where(
                                CaseContact.case_id == case_id,
                                CaseContact.role == "client",
                            )
                        )
                        clients = clients_result.scalars().all()

                        for client in clients:
                            client_contact_result = await session.execute(
                                select(Contact).where(Contact.id == client.contact_id)
                            )
                            client_contact = client_contact_result.scalar_one_or_none()

                            if client_contact:
                                client_label = (
                                    "Company"
                                    if client_contact.type == "legal"
                                    else "Person"
                                )
                                opposes_query = f"""
                                MATCH (client:{client_label} {{id: $client_id}}), (adverse:{node_label} {{id: $adverse_id}})
                                MERGE (client)-[r:OPPOSES]->(adverse)
                                SET r.case_id = $case_id,
                                    r.case_reference = $case_reference,
                                    r.since = datetime($since)
                                """
                                await self.neo4j_client.execute_query(
                                    opposes_query,
                                    {
                                        "client_id": str(client_contact.id),
                                        "adverse_id": str(contact.id),
                                        "case_id": str(case.id),
                                        "case_reference": case.reference,
                                        "since": case.opened_at.isoformat()
                                        if case.opened_at
                                        else datetime.now().isoformat(),
                                    },
                                )
                                relationships_created += 1

                logger.info(
                    f"Created {relationships_created} relationships for case {case_id}"
                )
                return relationships_created

        except Exception as e:
            logger.error(f"Failed to sync relationships for case {case_id}: {e}")
            return 0

    async def batch_sync(self, limit: int = 1000) -> dict:
        """Initial bulk sync from PostgreSQL to Neo4j."""
        try:
            start_time = datetime.now()
            stats = {
                "persons": 0,
                "companies": 0,
                "cases": 0,
                "lawyers": 0,
                "relationships": 0,
                "errors": 0,
                "duration_seconds": 0,
            }

            async with get_superadmin_session() as session:
                # Sync all persons
                persons_result = await session.execute(
                    select(Contact).where(Contact.type == "natural").limit(limit)
                )
                persons = persons_result.scalars().all()

                for person in persons:
                    success = await self.sync_person_to_graph(person.id)
                    if success:
                        stats["persons"] += 1
                    else:
                        stats["errors"] += 1

                # Sync all companies
                companies_result = await session.execute(
                    select(Contact).where(Contact.type == "legal").limit(limit)
                )
                companies = companies_result.scalars().all()

                for company in companies:
                    success = await self.sync_company_to_graph(company.id)
                    if success:
                        stats["companies"] += 1
                    else:
                        stats["errors"] += 1

                # Sync all lawyers
                lawyers_result = await session.execute(select(User).limit(limit))
                lawyers = lawyers_result.scalars().all()

                for lawyer in lawyers:
                    try:
                        lawyer_query = """
                        MERGE (l:Lawyer {id: $id})
                        SET l.name = $name,
                            l.email = $email,
                            l.role = $role,
                            l.updated_at = datetime()
                        """
                        await self.neo4j_client.execute_query(
                            lawyer_query,
                            {
                                "id": str(lawyer.id),
                                "name": lawyer.full_name,
                                "email": lawyer.email,
                                "role": lawyer.role,
                            },
                        )
                        stats["lawyers"] += 1
                    except Exception as e:
                        logger.error(f"Failed to sync lawyer {lawyer.id}: {e}")
                        stats["errors"] += 1

                # Sync all cases
                cases_result = await session.execute(select(Case).limit(limit))
                cases = cases_result.scalars().all()

                for case in cases:
                    success = await self.sync_case_to_graph(case.id)
                    if success:
                        stats["cases"] += 1
                    else:
                        stats["errors"] += 1

                # Sync all relationships
                for case in cases:
                    rel_count = await self.sync_relationships(case.id)
                    stats["relationships"] += rel_count

            end_time = datetime.now()
            stats["duration_seconds"] = (end_time - start_time).total_seconds()

            logger.info(f"Batch sync completed: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Batch sync failed: {e}")
            raise


# Singleton instance
_graph_sync_service: Optional[GraphSyncService] = None
_lock = asyncio.Lock()


async def get_graph_sync_service() -> GraphSyncService:
    """Get graph sync service singleton."""
    global _graph_sync_service
    async with _lock:
        if _graph_sync_service is None:
            _graph_sync_service = GraphSyncService()
            await _graph_sync_service.initialize()
        return _graph_sync_service
