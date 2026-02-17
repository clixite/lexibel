"""SENTINEL conflict detection API routes.

This module provides REST API endpoints for the SENTINEL system:
- Conflict checking and detection
- Conflict listing and resolution
- Graph synchronization
- Graph visualization
- Entity search
- Real-time alert streaming
"""

import asyncio
import logging
import math
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db_session, get_current_user
from apps.api.schemas.sentinel import (
    ConflictCheckRequest,
    ConflictCheckResponse,
    ConflictListResponse,
    ConflictResolveRequest,
    ConflictResolveResponse,
    SyncRequest,
    SyncResponse,
    GraphDataResponse,
    EntitySearchResponse,
    AlertStreamEvent,
    ConflictDetail,
    ConflictSummary,
    PaginationInfo,
    EntityRef,
    EntitySearchResult,
    GraphNode,
    GraphEdge,
)
from apps.api.services.sentinel.conflict_detector import get_conflict_detector
from apps.api.services.sentinel.graph_sync import get_graph_sync_service
from apps.api.services.sentinel.alerter import ConflictAlerter
from packages.db.models.sentinel_conflict import SentinelConflict
from packages.db.models.contact import Contact

logger = logging.getLogger(__name__)

router = APIRouter()


def get_conflict_status(conflict: SentinelConflict) -> str:
    """Determine conflict status from resolution field.

    Args:
        conflict: The SentinelConflict object

    Returns:
        Status string: 'active', 'resolved', or 'dismissed'
    """
    if not conflict.resolution:
        return "active"
    return "dismissed" if conflict.resolution == "false_positive" else "resolved"


# ── 1. POST /check-conflict ──


@router.post("/check-conflict", response_model=ConflictCheckResponse)
async def check_conflict(
    request: ConflictCheckRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Check for conflicts when adding a contact to a case.

    This endpoint runs all 8 conflict detection patterns against the
    knowledge graph and returns detected conflicts with severity scores.

    Args:
        request: Contains contact_id, optional case_id, and include_graph flag
        db: Database session (auto-injected with RLS)
        current_user: Current authenticated user (auto-injected)

    Returns:
        ConflictCheckResponse with list of conflicts and metadata

    Raises:
        HTTPException: 404 if contact not found, 500 for server errors
    """
    request_id = f"check-{request.contact_id}"
    logger.info(
        f"[{request_id}] Conflict check requested by user {current_user['user_id']} "
        f"for contact {request.contact_id}"
    )

    try:
        # Verify contact exists and belongs to tenant (RLS will filter)
        contact_result = await db.execute(
            select(Contact).where(Contact.id == request.contact_id)
        )
        contact = contact_result.scalar_one_or_none()

        if not contact:
            logger.warning(f"[{request_id}] Contact {request.contact_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contact {request.contact_id} not found",
            )

        # Determine contact type for conflict detection
        contact_type = "company" if contact.type == "legal" else "person"

        # Get conflict detector service
        detector = await get_conflict_detector()

        # Run conflict detection
        conflicts_data = await detector.check_all_conflicts(
            contact_id=request.contact_id,
            case_id=request.case_id,
            contact_type=contact_type,
        )

        # Map conflict data to ConflictDetail schemas
        conflict_details = []
        for conflict in conflicts_data:
            # Build entities involved list
            entities = []

            # Add trigger entity (the contact being checked)
            entities.append(
                EntityRef(
                    id=request.contact_id,
                    name=contact.full_name,
                    type="Company" if contact.type == "legal" else "Person",
                )
            )

            # Add conflicting entity if available
            if conflict.get("client_id"):
                entities.append(
                    EntityRef(
                        id=UUID(conflict["client_id"]),
                        name=conflict.get("client_name", "Unknown"),
                        type="Company" if conflict.get("client_type") == "legal" else "Person",
                    )
                )

            conflict_detail = ConflictDetail(
                id=uuid.uuid4(),  # Temporary ID - will be assigned when saved
                conflict_type=conflict["conflict_type"],
                severity_score=conflict["severity_score"],
                description=conflict["description"],
                entities_involved=entities,
                detected_at=datetime.now(),
            )
            conflict_details.append(conflict_detail)

        # Calculate highest severity
        highest_severity = max(
            (c.severity_score for c in conflict_details), default=0
        )

        # Fetch graph data if requested
        graph_data = None
        if request.include_graph and conflict_details:
            try:
                # Get unique entity IDs from all conflicts
                entity_ids = set()
                for conflict in conflict_details:
                    for entity in conflict.entities_involved:
                        entity_ids.add(entity.id)

                # Fetch graph data for these entities using Neo4j
                detector = await get_conflict_detector()
                neo4j_client = detector.neo4j_client

                # Query Neo4j for nodes and relationships involving these entities
                # Restructured to avoid inefficient collect(DISTINCT ...) operations
                query = """
                MATCH (n)
                WHERE n.id IN $entity_ids
                WITH n
                OPTIONAL MATCH (n)-[r]-(connected)
                WHERE connected IS NOT NULL AND connected.id IN $entity_ids
                RETURN
                    n.id as node_id,
                    labels(n)[0] as node_type,
                    n.name as node_name,
                    connected.id as connected_id,
                    type(r) as rel_type
                """

                results = await neo4j_client.execute_query(
                    query, {"entity_ids": [str(eid) for eid in entity_ids]}
                )

                if results:
                    # Process row-based results into nodes and edges
                    nodes_dict = {}
                    edges_set = set()

                    for record in results:
                        # Add node
                        node_id = record.get("node_id")
                        if node_id and node_id not in nodes_dict:
                            nodes_dict[node_id] = {
                                "id": node_id,
                                "type": record.get("node_type", "Entity"),
                                "name": record.get("node_name", "Unknown")
                            }

                        # Add edge if relationship exists
                        connected_id = record.get("connected_id")
                        rel_type = record.get("rel_type")
                        if node_id and connected_id and rel_type:
                            # Use frozenset to avoid duplicate edges
                            edge_key = frozenset([node_id, connected_id, rel_type])
                            if edge_key not in edges_set:
                                edges_set.add(edge_key)

                    # Convert edges_set to list of edge dicts
                    edges_list = []
                    for edge_key in edges_set:
                        edge_parts = list(edge_key)
                        if len(edge_parts) >= 3:
                            edges_list.append({
                                "from": edge_parts[0],
                                "to": edge_parts[1],
                                "type": edge_parts[2]
                            })

                    graph_data = {
                        "nodes": list(nodes_dict.values()),
                        "edges": edges_list
                    }
                else:
                    # Fallback to basic structure
                    graph_data = {
                        "nodes": [{"id": str(eid), "type": "Entity", "name": "Unknown"} for eid in entity_ids],
                        "edges": []
                    }
            except Exception as e:
                logger.warning(f"[{request_id}] Failed to fetch graph data: {e}")
                graph_data = None

        logger.info(
            f"[{request_id}] Found {len(conflict_details)} conflicts, "
            f"highest severity: {highest_severity}"
        )

        return ConflictCheckResponse(
            conflicts=conflict_details,
            total_count=len(conflict_details),
            highest_severity=highest_severity,
            check_timestamp=datetime.now(),
            graph_data=graph_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[{request_id}] Error checking conflicts: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check conflicts",
        )


# ── 2. GET /conflicts ──


@router.get("/conflicts", response_model=ConflictListResponse)
async def list_conflicts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by status: active, resolved, dismissed"
    ),
    severity_min: Optional[int] = Query(
        None, ge=0, le=100, description="Minimum severity score"
    ),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """List all detected conflicts with pagination.

    Supports filtering by status and minimum severity score.
    Results are ordered by severity (highest first), then by detection date.

    Args:
        page: Page number (1-indexed)
        page_size: Number of conflicts per page (max 100)
        status_filter: Filter by 'active', 'resolved', or 'dismissed'
        severity_min: Only return conflicts with severity >= this value
        db: Database session (auto-injected with RLS)
        current_user: Current authenticated user (auto-injected)

    Returns:
        ConflictListResponse with paginated conflicts and metadata
    """
    request_id = f"list-{current_user['user_id']}"
    logger.info(
        f"[{request_id}] Listing conflicts: page={page}, status={status_filter}, "
        f"severity_min={severity_min}"
    )

    try:
        # Build base query
        query = select(SentinelConflict)

        # Apply status filter
        if status_filter:
            if status_filter == "active":
                query = query.where(
                    or_(
                        SentinelConflict.resolution.is_(None),
                        SentinelConflict.resolution == "",
                    )
                )
            elif status_filter in ("resolved", "dismissed"):
                query = query.where(SentinelConflict.resolution.isnot(None))

        # Apply severity filter
        if severity_min is not None:
            query = query.where(SentinelConflict.severity_score >= severity_min)

        # Order by severity (desc), then by created_at (desc)
        query = query.order_by(
            SentinelConflict.severity_score.desc(),
            SentinelConflict.created_at.desc(),
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.limit(page_size).offset(offset)

        # Execute query
        result = await db.execute(query)
        conflicts = result.scalars().all()

        # Batch load all contacts to avoid N+1 queries
        contact_ids = set()
        for conflict in conflicts:
            contact_ids.add(conflict.trigger_entity_id)
            if conflict.conflicting_entity_id:
                contact_ids.add(conflict.conflicting_entity_id)

        # Single batch query for all contacts
        contacts_map = {}
        if contact_ids:
            contact_result = await db.execute(
                select(Contact).where(Contact.id.in_(contact_ids))
            )
            contacts_map = {c.id: c for c in contact_result.scalars().all()}

        # Map to ConflictSummary schemas
        conflict_summaries = []
        for conflict in conflicts:
            # Determine status using helper function
            conflict_status = get_conflict_status(conflict)

            # Build entities list with actual contact data from batch-loaded map
            entities = []

            # Get trigger entity from map
            contact_obj = contacts_map.get(conflict.trigger_entity_id)
            if contact_obj:
                entities.append(
                    EntityRef(
                        id=contact_obj.id,
                        name=contact_obj.full_name,
                        type="Company" if contact_obj.type == "legal" else "Person",
                    )
                )

            # Get conflicting entity from map if available
            if conflict.conflicting_entity_id:
                conflicting_contact = contacts_map.get(conflict.conflicting_entity_id)
                if conflicting_contact:
                    entities.append(
                        EntityRef(
                            id=conflicting_contact.id,
                            name=conflicting_contact.full_name,
                            type="Company" if conflicting_contact.type == "legal" else "Person",
                        )
                    )

            summary = ConflictSummary(
                id=conflict.id,
                conflict_type=conflict.conflict_type,
                severity_score=conflict.severity_score,
                description=conflict.description,
                entities_involved=entities,
                detected_at=conflict.created_at,
                status=conflict_status,
                resolved_at=conflict.resolved_at,
            )
            conflict_summaries.append(summary)

        # Calculate total pages
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        pagination = PaginationInfo(
            page=page,
            per_page=page_size,
            total=total,
            total_pages=total_pages,
        )

        logger.info(f"[{request_id}] Returning {len(conflicts)} conflicts (page {page}/{total_pages})")

        return ConflictListResponse(
            conflicts=conflict_summaries,
            pagination=pagination,
        )

    except Exception as e:
        logger.error(f"[{request_id}] Error listing conflicts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list conflicts",
        )


# ── 3. PUT /conflicts/{conflict_id}/resolve ──


@router.put("/conflicts/{conflict_id}/resolve", response_model=ConflictResolveResponse)
async def resolve_conflict(
    conflict_id: UUID,
    request: ConflictResolveRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Mark a conflict as resolved.

    Requires the resolution type (refused, waiver_obtained, false_positive)
    and optional notes. The current user is automatically recorded as the resolver.

    Args:
        conflict_id: UUID of the conflict to resolve
        request: Resolution details (type and optional notes)
        db: Database session (auto-injected with RLS)
        current_user: Current authenticated user (auto-injected)

    Returns:
        ConflictResolveResponse with updated conflict status

    Raises:
        HTTPException: 404 if conflict not found, 403 if permission denied
    """
    request_id = f"resolve-{conflict_id}"
    logger.info(
        f"[{request_id}] Resolving conflict {conflict_id} as {request.resolution} "
        f"by user {current_user['user_id']}"
    )

    try:
        # Get conflict (RLS will ensure tenant isolation)
        result = await db.execute(
            select(SentinelConflict).where(SentinelConflict.id == conflict_id)
        )
        conflict = result.scalar_one_or_none()

        if not conflict:
            logger.warning(f"[{request_id}] Conflict {conflict_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conflict {conflict_id} not found",
            )

        # Use ConflictAlerter to resolve
        alerter = ConflictAlerter(db)
        success = await alerter.resolve_conflict(
            conflict_id=conflict_id,
            resolution=request.resolution,
            resolved_by=UUID(current_user['user_id']),  # Use authenticated user
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to resolve conflict",
            )

        # Refresh conflict to get updated data
        await db.refresh(conflict)

        # Determine new status using helper function
        new_status = get_conflict_status(conflict)

        logger.info(f"[{request_id}] Conflict resolved successfully as {new_status}")

        return ConflictResolveResponse(
            id=conflict.id,
            status=new_status,
            resolved_at=conflict.resolved_at,
            resolved_by=conflict.resolved_by,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Error resolving conflict: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve conflict",
        )


# ── 4. POST /sync ──


@router.post("/sync", response_model=SyncResponse)
async def sync_graph(
    request: SyncRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Manually trigger graph synchronization.

    Can sync specific entities by ID or perform a bulk sync of all entities.
    Performance varies based on the number of entities (expect ~1-5 seconds
    for 1000 entities).

    Args:
        request: Sync parameters (entity_ids, sync_all, limit)
        db: Database session (auto-injected with RLS)
        current_user: Current authenticated user (auto-injected)

    Returns:
        SyncResponse with sync statistics and duration

    Raises:
        HTTPException: 403 if permission denied, 500 for sync errors
    """
    request_id = f"sync-{current_user['user_id']}"
    logger.info(
        f"[{request_id}] Graph sync requested: sync_all={request.sync_all}, "
        f"entity_count={len(request.entity_ids or [])}"
    )

    try:
        start_time = datetime.now()
        sync_service = await get_graph_sync_service()

        synced_count = 0
        failed_count = 0

        if request.sync_all:
            # Batch sync all entities
            logger.info(f"[{request_id}] Starting batch sync (limit={request.limit})")
            stats = await sync_service.batch_sync(limit=request.limit)

            synced_count = (
                stats.get("persons", 0)
                + stats.get("companies", 0)
                + stats.get("cases", 0)
                + stats.get("lawyers", 0)
            )
            failed_count = stats.get("errors", 0)

        elif request.entity_ids:
            # Sync specific entities
            logger.info(f"[{request_id}] Syncing {len(request.entity_ids)} specific entities")

            for entity_id in request.entity_ids:
                # Try syncing as person first
                success = await sync_service.sync_person_to_graph(entity_id)

                if not success:
                    # Try as company
                    success = await sync_service.sync_company_to_graph(entity_id)

                if not success:
                    # Try as case
                    success = await sync_service.sync_case_to_graph(entity_id)

                if success:
                    synced_count += 1
                else:
                    failed_count += 1
                    logger.warning(f"[{request_id}] Failed to sync entity {entity_id}")

            # Ensure changes are persisted
            await db.commit()

        else:
            # No entities specified
            logger.warning(f"[{request_id}] No entities specified for sync")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(
            f"[{request_id}] Sync completed: {synced_count} synced, "
            f"{failed_count} failed in {duration:.2f}s"
        )

        return SyncResponse(
            synced_count=synced_count,
            failed_count=failed_count,
            duration_seconds=duration,
        )

    except Exception as e:
        logger.error(f"[{request_id}] Error during sync: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync graph",
        )


# ── 5. GET /graph/{entity_id} ──


@router.get("/graph/{entity_id}", response_model=GraphDataResponse)
async def get_graph_data(
    entity_id: UUID,
    depth: int = Query(1, ge=1, le=3, description="Relationship depth (1-3)"),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Get graph data for visualization.

    Returns the entity and its neighbors up to the specified depth.
    Useful for rendering conflict visualizations in the UI.

    Args:
        entity_id: UUID of the central entity
        depth: How many relationship hops to include (1-3)
        db: Database session (auto-injected with RLS)
        current_user: Current authenticated user (auto-injected)

    Returns:
        GraphDataResponse with nodes and edges for visualization

    Raises:
        HTTPException: 404 if entity not found, 500 for query errors
    """
    request_id = f"graph-{entity_id}"
    logger.info(
        f"[{request_id}] Graph data requested by user {current_user['user_id']} "
        f"(depth={depth})"
    )

    try:
        # Verify entity exists
        contact_result = await db.execute(
            select(Contact).where(Contact.id == entity_id)
        )
        contact = contact_result.scalar_one_or_none()

        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found",
            )

        # Get Neo4j client and query graph
        detector = await get_conflict_detector()
        neo4j_client = detector.neo4j_client

        # Query for entity and neighbors
        # Note: Neo4j Cypher doesn't support parameterizing path length in [*1..n] syntax,
        # but depth is validated by FastAPI Query(ge=1, le=3) so f-string is safe here
        query = f"""
        MATCH (center {{id: $entity_id}})
        WHERE center:Person OR center:Company
        OPTIONAL MATCH path = (center)-[*1..{depth}]-(neighbor)
        WHERE neighbor:Person OR neighbor:Company OR neighbor:Case OR neighbor:Lawyer
        WITH center, collect(DISTINCT neighbor) as neighbors, collect(DISTINCT path) as paths
        UNWIND paths as p
        UNWIND relationships(p) as rel
        RETURN center,
               neighbors,
               collect(DISTINCT {{
                   from: startNode(rel).id,
                   to: endNode(rel).id,
                   type: type(rel),
                   properties: properties(rel)
               }}) as edges
        """

        results = await neo4j_client.execute_query(
            query, {"entity_id": str(entity_id)}
        )

        # Build nodes and edges
        nodes = []
        edges = []

        if results:
            record = results[0]

            # Add center node with proper null/empty checks
            center = record.get("center", {})
            if not center or not center.get("id"):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Entity {entity_id} not found in graph"
                )

            center_type = center.get("type", "Unknown")
            center_label = "Company" if center_type == "legal" else "Person"
            nodes.append(
                GraphNode(
                    id=str(entity_id),
                    label=center_label,
                    name=center.get("name", "Unknown"),
                    properties={
                        "email": center.get("email"),
                        "phone": center.get("phone"),
                    },
                )
            )

            # Add neighbor nodes
            neighbors = record.get("neighbors", [])
            for neighbor in neighbors:
                if neighbor:
                    node_id = neighbor.get("id")
                    if node_id:
                        # Determine label
                        labels = neighbor.get("labels", [])
                        label = labels[0] if labels else "Entity"

                        nodes.append(
                            GraphNode(
                                id=str(node_id),
                                label=label,
                                name=neighbor.get("name", "Unknown"),
                                properties={
                                    k: v for k, v in neighbor.items()
                                    if k not in ("id", "name", "labels")
                                },
                            )
                        )

            # Add edges with proper null checks
            edge_records = record.get("edges", [])
            for edge in edge_records:
                if edge and edge.get("from") and edge.get("to"):
                    edges.append(
                        GraphEdge(
                            from_id=str(edge["from"]),
                            to_id=str(edge["to"]),
                            type=edge.get("type", "RELATED"),
                            properties=edge.get("properties", {}),
                        )
                    )

        logger.info(
            f"[{request_id}] Returning {len(nodes)} nodes and {len(edges)} edges"
        )

        return GraphDataResponse(
            nodes=nodes,
            edges=edges,
            center_entity_id=entity_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Error fetching graph data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch graph data",
        )


# ── 6. GET /search ──


@router.get("/search", response_model=EntitySearchResponse)
async def search_entities(
    q: str = Query(..., min_length=1, description="Search query"),
    entity_type: Optional[str] = Query(
        None, description="Filter by entity type: Person or Company"
    ),
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Search persons and companies by name, email, or BCE number.

    Performs case-insensitive search across contact names, emails, and
    BCE numbers. Returns results with conflict counts for each entity.

    Args:
        q: Search query string
        entity_type: Optional filter ('Person' or 'Company')
        limit: Maximum number of results (max 50)
        db: Database session (auto-injected with RLS)
        current_user: Current authenticated user (auto-injected)

    Returns:
        EntitySearchResponse with matching entities and conflict counts
    """
    request_id = f"search-{current_user['user_id']}"
    logger.info(
        f"[{request_id}] Entity search: q='{q}', type={entity_type}, limit={limit}"
    )

    try:
        # Build search query
        search_pattern = f"%{q}%"
        query = select(Contact).where(
            or_(
                Contact.full_name.ilike(search_pattern),
                Contact.email.ilike(search_pattern),
                Contact.bce_number.ilike(search_pattern),
            )
        )

        # Apply entity type filter
        if entity_type:
            if entity_type.lower() == "person":
                query = query.where(Contact.type == "natural")
            elif entity_type.lower() == "company":
                query = query.where(Contact.type == "legal")

        # Apply limit
        query = query.limit(limit)

        # Execute search
        result = await db.execute(query)
        contacts = result.scalars().all()

        # Get conflict counts and last check timestamps for each contact in batch
        contact_ids = [contact.id for contact in contacts]
        conflict_counts = {}
        last_checked_times = {}

        if contact_ids:
            # Batch query for conflict counts
            count_result = await db.execute(
                select(
                    SentinelConflict.trigger_entity_id,
                    func.count(SentinelConflict.id).label("count"),
                )
                .where(
                    and_(
                        SentinelConflict.trigger_entity_id.in_(contact_ids),
                        or_(
                            SentinelConflict.resolution.is_(None),
                            SentinelConflict.resolution == "",
                        ),
                    )
                )
                .group_by(SentinelConflict.trigger_entity_id)
            )

            for row in count_result:
                conflict_counts[row[0]] = row[1]

            # Batch query for last checked timestamps
            last_check_result = await db.execute(
                select(
                    SentinelConflict.trigger_entity_id,
                    func.max(SentinelConflict.created_at).label("last_checked"),
                )
                .where(SentinelConflict.trigger_entity_id.in_(contact_ids))
                .group_by(SentinelConflict.trigger_entity_id)
            )

            for row in last_check_result:
                last_checked_times[row[0]] = row[1]

        # Map to EntitySearchResult
        search_results = []
        for contact in contacts:
            result_item = EntitySearchResult(
                id=contact.id,
                name=contact.full_name,
                type="Company" if contact.type == "legal" else "Person",
                bce_number=contact.bce_number,
                email=contact.email,
                phone=contact.phone_e164,
                conflict_count=conflict_counts.get(contact.id, 0),
                last_checked=last_checked_times.get(contact.id),
            )
            search_results.append(result_item)

        logger.info(f"[{request_id}] Found {len(search_results)} matching entities")

        return EntitySearchResponse(
            results=search_results,
            total=len(search_results),
        )

    except Exception as e:
        logger.error(f"[{request_id}] Error searching entities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search entities",
        )


# ── 7. GET /alerts/stream ──


@router.get("/alerts/stream")
async def stream_alerts(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Server-Sent Events stream for real-time conflict alerts.

    Establishes a persistent connection that sends alert events as they occur.
    The connection stays open until the client disconnects or an error occurs.

    Args:
        db: Database session (auto-injected with RLS)
        current_user: Current authenticated user (auto-injected)

    Returns:
        EventSourceResponse: SSE stream of AlertStreamEvent objects
    """
    user_id = UUID(current_user["user_id"])
    request_id = f"stream-{user_id}"
    logger.info(f"[{request_id}] SSE stream opened")

    async def event_generator():
        """Generate SSE events for the client."""
        # Note: ConflictAlerter uses db session only for quick registration operations.
        # The SSE connection itself doesn't hold the session long-term; it's only used
        # for initial setup and potential alert queries when conflicts are detected.
        alerter = ConflictAlerter(db)
        connection_placeholder = object()  # Placeholder connection object

        try:
            # Register SSE connection with the alerter
            alerter.register_sse_connection(user_id, connection_placeholder)
            logger.info(f"[{request_id}] SSE connection registered")

            # Send initial connection event using AlertStreamEvent schema
            connected_event = AlertStreamEvent(
                event_type="conflict_detected",  # Using available event type
                data={
                    "message": "Connected to SENTINEL alert stream",
                    "status": "connected"
                },
                timestamp=datetime.now()
            )
            yield {
                "event": "connected",
                "data": connected_event.model_dump_json(),
            }

            # Keep connection alive with heartbeat
            # In production, this would listen for new conflicts via alerter.send_realtime_alert
            # and push them to the client through the registered connection
            while True:
                # Heartbeat every 30 seconds to keep connection alive
                await asyncio.sleep(30)

                heartbeat_event = AlertStreamEvent(
                    event_type="conflict_detected",
                    data={"heartbeat": True},
                    timestamp=datetime.now()
                )
                yield {
                    "event": "heartbeat",
                    "data": heartbeat_event.model_dump_json(),
                }

        except Exception as e:
            logger.error(f"[{request_id}] SSE stream error: {e}", exc_info=True)
            error_event = AlertStreamEvent(
                event_type="conflict_detected",
                data={"error": "Stream error occurred"},
                timestamp=datetime.now()
            )
            yield {
                "event": "error",
                "data": error_event.model_dump_json(),
            }
        finally:
            # Unregister connection when client disconnects
            alerter.unregister_sse_connection(user_id, connection_placeholder)
            logger.info(f"[{request_id}] SSE stream closed")

    return EventSourceResponse(event_generator())
