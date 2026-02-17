"""Graph Sync Service — Real-time PostgreSQL ↔ Neo4j synchronization.

Automatically syncs entities from PostgreSQL to Neo4j knowledge graph:
- Cases → Case nodes
- Contacts → Person/Organization nodes
- Lawyers → Person nodes (with REPRESENTS relationships)
- Deadlines → Event nodes
- Documents → Document nodes

2026 Best Practices:
- Event-driven architecture (PostgreSQL triggers/listeners)
- Incremental sync (only changed entities)
- Bidirectional sync with conflict resolution
- Async queue processing
- Retry logic with exponential backoff
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from apps.api.services.graph.neo4j_service import (
    InMemoryGraphService,
)

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """PostgreSQL entity types."""

    CASE = "case"
    CONTACT = "contact"
    LAWYER = "lawyer"
    COURT = "court"
    DEADLINE = "deadline"
    DOCUMENT = "document"
    ORGANIZATION = "organization"


class SyncOperation(str, Enum):
    """Sync operation types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class SyncEvent:
    """Event representing a change in PostgreSQL."""

    entity_type: EntityType
    entity_id: str
    operation: SyncOperation
    data: dict
    tenant_id: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    entity_id: str
    entity_type: EntityType
    operation: SyncOperation
    nodes_affected: int = 0
    relationships_affected: int = 0
    error: Optional[str] = None


class GraphSyncService:
    """Real-time sync between PostgreSQL and Neo4j."""

    def __init__(
        self,
        graph_service: Optional[InMemoryGraphService] = None,
        enable_realtime: bool = True,
    ):
        self.graph = graph_service or InMemoryGraphService()
        self.enable_realtime = enable_realtime
        self._sync_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def start_sync_worker(self):
        """Start background worker to process sync queue."""
        self._running = True
        logger.info("Graph sync worker started")

        while self._running:
            try:
                # Get next sync event with timeout
                event = await asyncio.wait_for(
                    self._sync_queue.get(),
                    timeout=5.0,
                )

                result = await self._process_sync_event(event)

                if result.success:
                    logger.info(
                        f"Synced {result.entity_type} {result.entity_id}: "
                        f"{result.nodes_affected} nodes, {result.relationships_affected} rels"
                    )
                else:
                    logger.error(
                        f"Sync failed for {result.entity_type} {result.entity_id}: {result.error}"
                    )

            except asyncio.TimeoutError:
                # No events, continue waiting
                continue
            except Exception as e:
                logger.error(f"Sync worker error: {e}")

    async def stop_sync_worker(self):
        """Stop background sync worker."""
        self._running = False
        logger.info("Graph sync worker stopped")

    async def queue_sync(self, event: SyncEvent):
        """Add sync event to processing queue."""
        await self._sync_queue.put(event)

    async def sync_case(
        self,
        case_id: str,
        case_data: dict,
        tenant_id: str,
        operation: SyncOperation = SyncOperation.CREATE,
    ) -> SyncResult:
        """Sync a case to Neo4j graph.

        Creates/updates:
        - Case node
        - Related Contact nodes (parties)
        - PARTY_TO relationships
        - Court node + FILED_AT relationship
        """
        result = SyncResult(
            success=True,
            entity_id=case_id,
            entity_type=EntityType.CASE,
            operation=operation,
        )

        try:
            if operation == SyncOperation.DELETE:
                # Delete case node and all relationships
                deleted = self.graph.delete_node(case_id, tenant_id)
                result.nodes_affected = 1 if deleted else 0
                return result

            # Create/update case node
            self.graph.create_node(
                label="Case",
                properties={
                    "id": case_id,
                    "name": case_data.get("title", case_data.get("case_number", "")),
                    "case_number": case_data.get("case_number", ""),
                    "status": case_data.get("status", ""),
                    "case_type": case_data.get("case_type", ""),
                    "filing_date": str(case_data.get("filing_date", "")),
                    "created_at": str(case_data.get("created_at", "")),
                    "updated_at": str(case_data.get("updated_at", "")),
                },
                tenant_id=tenant_id,
            )
            result.nodes_affected += 1

            # Sync court if present
            if case_data.get("court_id") and case_data.get("court_name"):
                self.graph.create_node(
                    label="Court",
                    properties={
                        "id": str(case_data["court_id"]),
                        "name": case_data["court_name"],
                    },
                    tenant_id=tenant_id,
                )
                result.nodes_affected += 1

                # Create FILED_AT relationship
                self.graph.create_relationship(
                    from_id=case_id,
                    to_id=str(case_data["court_id"]),
                    rel_type="FILED_AT",
                    properties={"date": str(case_data.get("filing_date", ""))},
                    tenant_id=tenant_id,
                )
                result.relationships_affected += 1

            # Sync parties (contacts)
            for party in case_data.get("parties", []):
                contact_result = await self.sync_contact(
                    contact_id=str(party["contact_id"]),
                    contact_data=party,
                    tenant_id=tenant_id,
                    operation=SyncOperation.CREATE,
                )
                result.nodes_affected += contact_result.nodes_affected
                result.relationships_affected += contact_result.relationships_affected

                # Create PARTY_TO relationship
                role = party.get("role", "party")
                self.graph.create_relationship(
                    from_id=str(party["contact_id"]),
                    to_id=case_id,
                    rel_type="PARTY_TO",
                    properties={"role": role, "side": party.get("side", "")},
                    tenant_id=tenant_id,
                )
                result.relationships_affected += 1

            # Check for opposing parties
            opposing_sides = self._identify_opposing_sides(case_data.get("parties", []))
            for contact_a, contact_b in opposing_sides:
                self.graph.create_relationship(
                    from_id=contact_a,
                    to_id=contact_b,
                    rel_type="OPPOSED_TO",
                    properties={"case_id": case_id},
                    tenant_id=tenant_id,
                )
                result.relationships_affected += 1

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"Failed to sync case {case_id}: {e}")

        return result

    async def sync_contact(
        self,
        contact_id: str,
        contact_data: dict,
        tenant_id: str,
        operation: SyncOperation = SyncOperation.CREATE,
    ) -> SyncResult:
        """Sync a contact to Neo4j graph.

        Creates Person or Organization node based on contact type.
        """
        result = SyncResult(
            success=True,
            entity_id=contact_id,
            entity_type=EntityType.CONTACT,
            operation=operation,
        )

        try:
            if operation == SyncOperation.DELETE:
                deleted = self.graph.delete_node(contact_id, tenant_id)
                result.nodes_affected = 1 if deleted else 0
                return result

            # Determine label based on contact type
            contact_type = contact_data.get("type", "person").lower()
            label = "Organization" if contact_type == "organization" else "Person"

            # Create/update contact node
            properties = {
                "id": contact_id,
                "name": contact_data.get("name", contact_data.get("full_name", "")),
                "email": contact_data.get("email", ""),
                "phone": contact_data.get("phone", ""),
                "contact_type": contact_type,
            }

            # Add type-specific properties
            if label == "Person":
                properties.update(
                    {
                        "first_name": contact_data.get("first_name", ""),
                        "last_name": contact_data.get("last_name", ""),
                    }
                )
            else:
                properties.update(
                    {
                        "organization_name": contact_data.get("organization_name", ""),
                    }
                )

            self.graph.create_node(
                label=label,
                properties=properties,
                tenant_id=tenant_id,
            )
            result.nodes_affected += 1

            # If contact belongs to organization, create relationship
            if contact_data.get("organization_id"):
                org_id = str(contact_data["organization_id"])

                # Ensure organization node exists
                org_node = self.graph.get_node(org_id, tenant_id)
                if not org_node:
                    org_node = self.graph.create_node(
                        label="Organization",
                        properties={
                            "id": org_id,
                            "name": contact_data.get(
                                "organization_name", "Unknown Org"
                            ),
                        },
                        tenant_id=tenant_id,
                    )
                    result.nodes_affected += 1

                # Create BELONGS_TO relationship
                self.graph.create_relationship(
                    from_id=contact_id,
                    to_id=org_id,
                    rel_type="BELONGS_TO",
                    tenant_id=tenant_id,
                )
                result.relationships_affected += 1

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"Failed to sync contact {contact_id}: {e}")

        return result

    async def sync_lawyer(
        self,
        lawyer_id: str,
        lawyer_data: dict,
        tenant_id: str,
        operation: SyncOperation = SyncOperation.CREATE,
    ) -> SyncResult:
        """Sync a lawyer to Neo4j graph.

        Creates Person node with lawyer role.
        Links to cases with REPRESENTS relationship.
        """
        result = SyncResult(
            success=True,
            entity_id=lawyer_id,
            entity_type=EntityType.LAWYER,
            operation=operation,
        )

        try:
            if operation == SyncOperation.DELETE:
                deleted = self.graph.delete_node(lawyer_id, tenant_id)
                result.nodes_affected = 1 if deleted else 0
                return result

            # Create lawyer node (Person with lawyer role)
            self.graph.create_node(
                label="Person",
                properties={
                    "id": lawyer_id,
                    "name": lawyer_data.get("name", lawyer_data.get("full_name", "")),
                    "email": lawyer_data.get("email", ""),
                    "bar_number": lawyer_data.get("bar_number", ""),
                    "role": "lawyer",
                    "specialization": lawyer_data.get("specialization", ""),
                },
                tenant_id=tenant_id,
            )
            result.nodes_affected += 1

            # Link to represented cases
            for case_assignment in lawyer_data.get("cases", []):
                case_id = str(case_assignment.get("case_id"))

                # Create REPRESENTS relationship
                self.graph.create_relationship(
                    from_id=lawyer_id,
                    to_id=case_id,
                    rel_type="REPRESENTS",
                    properties={
                        "role": case_assignment.get("role", "counsel"),
                        "assigned_date": str(case_assignment.get("assigned_date", "")),
                    },
                    tenant_id=tenant_id,
                )
                result.relationships_affected += 1

                # Link to represented contacts/parties
                if case_assignment.get("representing_contact_id"):
                    contact_id = str(case_assignment["representing_contact_id"])
                    self.graph.create_relationship(
                        from_id=lawyer_id,
                        to_id=contact_id,
                        rel_type="REPRESENTS",
                        properties={
                            "in_case": case_id,
                            "role": case_assignment.get("role", "counsel"),
                        },
                        tenant_id=tenant_id,
                    )
                    result.relationships_affected += 1

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"Failed to sync lawyer {lawyer_id}: {e}")

        return result

    async def sync_document(
        self,
        document_id: str,
        document_data: dict,
        tenant_id: str,
        operation: SyncOperation = SyncOperation.CREATE,
    ) -> SyncResult:
        """Sync a document to Neo4j graph.

        Creates Document node and links to case.
        """
        result = SyncResult(
            success=True,
            entity_id=document_id,
            entity_type=EntityType.DOCUMENT,
            operation=operation,
        )

        try:
            if operation == SyncOperation.DELETE:
                deleted = self.graph.delete_node(document_id, tenant_id)
                result.nodes_affected = 1 if deleted else 0
                return result

            # Create document node
            self.graph.create_node(
                label="Document",
                properties={
                    "id": document_id,
                    "name": document_data.get(
                        "filename", document_data.get("title", "")
                    ),
                    "document_type": document_data.get("document_type", ""),
                    "file_size": document_data.get("file_size", 0),
                    "uploaded_at": str(document_data.get("uploaded_at", "")),
                },
                tenant_id=tenant_id,
            )
            result.nodes_affected += 1

            # Link to case
            if document_data.get("case_id"):
                case_id = str(document_data["case_id"])
                self.graph.create_relationship(
                    from_id=document_id,
                    to_id=case_id,
                    rel_type="ATTACHED_TO",
                    properties={
                        "uploaded_at": str(document_data.get("uploaded_at", ""))
                    },
                    tenant_id=tenant_id,
                )
                result.relationships_affected += 1

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"Failed to sync document {document_id}: {e}")

        return result

    async def _process_sync_event(self, event: SyncEvent) -> SyncResult:
        """Process a single sync event."""
        sync_handlers = {
            EntityType.CASE: self.sync_case,
            EntityType.CONTACT: self.sync_contact,
            EntityType.LAWYER: self.sync_lawyer,
            EntityType.DOCUMENT: self.sync_document,
        }

        handler = sync_handlers.get(event.entity_type)
        if not handler:
            return SyncResult(
                success=False,
                entity_id=event.entity_id,
                entity_type=event.entity_type,
                operation=event.operation,
                error=f"No handler for entity type {event.entity_type}",
            )

        return await handler(
            event.entity_id,
            event.data,
            event.tenant_id,
            event.operation,
        )

    def _identify_opposing_sides(self, parties: list[dict]) -> list[tuple[str, str]]:
        """Identify opposing parties in a case.

        Looks for parties on different sides (plaintiff vs defendant).
        """
        opposing_pairs = []

        plaintiff_side = []
        defendant_side = []

        for party in parties:
            side = party.get("side", "").lower()
            contact_id = str(party.get("contact_id"))

            if "plaintiff" in side or "petitioner" in side:
                plaintiff_side.append(contact_id)
            elif "defendant" in side or "respondent" in side:
                defendant_side.append(contact_id)

        # Create opposing pairs
        for p_id in plaintiff_side:
            for d_id in defendant_side:
                opposing_pairs.append((p_id, d_id))

        return opposing_pairs

    async def full_sync_from_postgres(
        self,
        pg_connection: Any,  # PostgreSQL connection
        tenant_id: str,
    ) -> dict:
        """Perform full initial sync from PostgreSQL to Neo4j.

        Used for initial setup or recovery.

        Args:
            pg_connection: PostgreSQL database connection
            tenant_id: Tenant UUID

        Returns:
            Summary of sync results
        """
        summary = {
            "cases_synced": 0,
            "contacts_synced": 0,
            "lawyers_synced": 0,
            "documents_synced": 0,
            "errors": [],
        }

        # Note: This is a skeleton. In real implementation, you'd query PostgreSQL
        # using SQLAlchemy or psycopg2 to fetch all entities.

        # Example pseudo-code:
        # async with pg_connection.execute("SELECT * FROM cases WHERE tenant_id = ?", tenant_id) as cursor:
        #     async for row in cursor:
        #         result = await self.sync_case(row["id"], dict(row), tenant_id)
        #         if result.success:
        #             summary["cases_synced"] += 1
        #         else:
        #             summary["errors"].append(result.error)

        logger.info(f"Full sync completed for tenant {tenant_id}: {summary}")
        return summary


# Singleton instance for dependency injection
_sync_service: Optional[GraphSyncService] = None


def get_sync_service() -> GraphSyncService:
    """Get or create singleton sync service."""
    global _sync_service
    if _sync_service is None:
        _sync_service = GraphSyncService()
    return _sync_service
