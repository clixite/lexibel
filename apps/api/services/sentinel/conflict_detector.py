"""SENTINEL conflict detection service."""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from apps.api.services.neo4j_client import get_neo4j_client, Neo4jClient

logger = logging.getLogger(__name__)


class ConflictDetector:
    """Detect conflicts of interest using Neo4j graph queries."""

    def __init__(self):
        self.neo4j_client: Optional[Neo4jClient] = None

    async def initialize(self):
        """Initialize Neo4j client."""
        self.neo4j_client = await get_neo4j_client()

    async def detect_direct_conflicts(
        self, contact_id: UUID, case_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Pattern 1: Direct adversary conflicts.

        Check if contact is adversary to our clients in active cases.
        Cypher: MATCH path where contact OPPOSES our client
        """
        query = """
        MATCH (new_contact {id: $contact_id})
        WHERE new_contact:Person OR new_contact:Company
        MATCH (our_client)<-[:REPRESENTS]-(our_lawyer:Lawyer)
        WHERE our_client:Person OR our_client:Company
        MATCH (our_client)-[:OPPOSES]->(new_contact)
        MATCH (case:Case)-[:INVOLVES]->(our_client)
        WHERE case.status IN ['active', 'pending']
        RETURN DISTINCT new_contact.id AS conflicting_id,
               case.id AS case_id,
               our_client.name AS client_name,
               our_client.id AS client_id,
               case.name AS case_name,
               'direct_adversary' AS conflict_type
        LIMIT 100
        """

        try:
            results = await self.neo4j_client.execute_query(
                query, {"contact_id": str(contact_id)}
            )

            conflicts = []
            for record in results:
                conflicts.append(
                    {
                        "conflicting_id": record["conflicting_id"],
                        "case_id": record["case_id"],
                        "client_name": record.get("client_name", "Unknown"),
                        "client_id": record.get("client_id"),
                        "case_name": record.get("case_name", "Unknown Case"),
                        "conflict_type": "direct_adversary",
                        "description": f"Contact is direct adversary to our client {record.get('client_name', 'Unknown')} in case {record.get('case_name', 'Unknown Case')}",
                        "graph_path": {
                            "type": "direct_adversary",
                            "client": record.get("client_name"),
                            "case": record.get("case_name"),
                        },
                    }
                )

            return conflicts
        except Exception as e:
            logger.error(f"Error detecting direct conflicts: {e}")
            return []

    async def detect_ownership_conflicts(
        self, company_id: UUID, max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """Pattern 2: Indirect ownership conflicts.

        Find ownership chains: A owns B owns C (up to 3 degrees).
        Cypher: Variable length path OWNS*1..3
        """
        query = """
        MATCH path = (company:Company {id: $company_id})-[:OWNS*1..3]->(target:Company)
        MATCH (our_client:Company)<-[:REPRESENTS]-(our_lawyer:Lawyer)
        MATCH (our_client)-[:OPPOSES]->(target)
        MATCH (case:Case)-[:INVOLVES]->(our_client)
        WHERE case.status IN ['active', 'pending']
        RETURN DISTINCT target.id AS conflicting_id,
               length(path) AS ownership_depth,
               [n IN nodes(path) | n.name] AS ownership_chain,
               our_client.name AS client_name,
               our_client.id AS client_id,
               case.id AS case_id,
               case.name AS case_name,
               'indirect_ownership' AS conflict_type
        LIMIT 100
        """

        try:
            results = await self.neo4j_client.execute_query(
                query, {"company_id": str(company_id)}
            )

            conflicts = []
            for record in results:
                ownership_chain = record.get("ownership_chain", [])
                chain_str = " -> ".join(ownership_chain)

                conflicts.append(
                    {
                        "conflicting_id": record["conflicting_id"],
                        "case_id": record.get("case_id"),
                        "client_name": record.get("client_name", "Unknown"),
                        "client_id": record.get("client_id"),
                        "ownership_depth": record.get("ownership_depth", 0),
                        "ownership_chain": ownership_chain,
                        "conflict_type": "indirect_ownership",
                        "description": f"Indirect ownership conflict through {record.get('ownership_depth', 0)} degrees: {chain_str}",
                        "graph_path": {
                            "type": "indirect_ownership",
                            "depth": record.get("ownership_depth", 0),
                            "chain": ownership_chain,
                            "client": record.get("client_name"),
                        },
                    }
                )

            return conflicts
        except Exception as e:
            logger.error(f"Error detecting ownership conflicts: {e}")
            return []

    async def detect_director_overlap(self, company_id: UUID) -> List[Dict[str, Any]]:
        """Pattern 3: Shared directors between adversaries."""
        query = """
        MATCH (company:Company {id: $company_id})<-[:DIRECTOR_OF]-(director:Person)
        MATCH (director)-[:DIRECTOR_OF]->(other_company:Company)
        MATCH (our_client:Company)<-[:REPRESENTS]-(our_lawyer:Lawyer)
        MATCH (our_client)-[:OPPOSES]->(other_company)
        MATCH (case:Case)-[:INVOLVES]->(our_client)
        WHERE company.id <> other_company.id
        AND case.status IN ['active', 'pending']
        RETURN DISTINCT director.name AS director_name,
               director.id AS director_id,
               other_company.id AS conflicting_id,
               other_company.name AS other_company_name,
               our_client.name AS client_name,
               our_client.id AS client_id,
               case.id AS case_id,
               case.name AS case_name,
               'director_overlap' AS conflict_type
        LIMIT 100
        """

        try:
            results = await self.neo4j_client.execute_query(
                query, {"company_id": str(company_id)}
            )

            conflicts = []
            for record in results:
                conflicts.append(
                    {
                        "conflicting_id": record["conflicting_id"],
                        "case_id": record.get("case_id"),
                        "client_name": record.get("client_name", "Unknown"),
                        "client_id": record.get("client_id"),
                        "director_name": record.get(
                            "director_name", "Unknown Director"
                        ),
                        "director_id": record.get("director_id"),
                        "conflict_type": "director_overlap",
                        "description": f"Shared director {record.get('director_name', 'Unknown')} between company and adversary {record.get('other_company_name', 'Unknown')}",
                        "graph_path": {
                            "type": "director_overlap",
                            "director": record.get("director_name"),
                            "director_id": record.get("director_id"),
                            "other_company": record.get("other_company_name"),
                            "client": record.get("client_name"),
                        },
                    }
                )

            return conflicts
        except Exception as e:
            logger.error(f"Error detecting director overlap: {e}")
            return []

    async def detect_family_ties(self, person_id: UUID) -> List[Dict[str, Any]]:
        """Pattern 4: Family relationship conflicts."""
        query = """
        MATCH (person:Person {id: $person_id})-[r:FAMILY]->(relative:Person)
        WHERE r.type IN ['spouse', 'parent', 'child', 'sibling']
        MATCH (our_client:Person)<-[:REPRESENTS]-(our_lawyer:Lawyer)
        MATCH (our_client)-[:OPPOSES]->(relative)
        MATCH (case:Case)-[:INVOLVES]->(our_client)
        WHERE case.status IN ['active', 'pending']
        RETURN DISTINCT relative.id AS conflicting_id,
               relative.name AS relative_name,
               r.type AS relationship_type,
               our_client.name AS client_name,
               our_client.id AS client_id,
               case.id AS case_id,
               case.name AS case_name,
               'family_tie' AS conflict_type
        LIMIT 100
        """

        try:
            results = await self.neo4j_client.execute_query(
                query, {"person_id": str(person_id)}
            )

            conflicts = []
            for record in results:
                conflicts.append(
                    {
                        "conflicting_id": record["conflicting_id"],
                        "case_id": record.get("case_id"),
                        "client_name": record.get("client_name", "Unknown"),
                        "client_id": record.get("client_id"),
                        "relationship_type": record.get("relationship_type", "unknown"),
                        "relative_name": record.get("relative_name", "Unknown"),
                        "conflict_type": "family_tie",
                        "description": f"Family tie: {record.get('relationship_type', 'unknown')} relationship with adversary {record.get('relative_name', 'Unknown')}",
                        "graph_path": {
                            "type": "family_tie",
                            "relationship": record.get("relationship_type"),
                            "relative": record.get("relative_name"),
                            "client": record.get("client_name"),
                        },
                    }
                )

            return conflicts
        except Exception as e:
            logger.error(f"Error detecting family ties: {e}")
            return []

    async def detect_business_partners(self, company_id: UUID) -> List[Dict[str, Any]]:
        """Pattern 5: Joint ventures, partnerships."""
        query = """
        MATCH (company:Company {id: $company_id})-[r:PARTNER]->(partner:Company)
        WHERE r.ownership_percent > 25
        MATCH (our_client:Company)<-[:REPRESENTS]-(our_lawyer:Lawyer)
        MATCH (our_client)-[:OPPOSES]->(partner)
        MATCH (case:Case)-[:INVOLVES]->(our_client)
        WHERE case.status IN ['active', 'pending']
        RETURN DISTINCT partner.id AS conflicting_id,
               partner.name AS partner_name,
               r.ownership_percent AS stake,
               our_client.name AS client_name,
               our_client.id AS client_id,
               case.id AS case_id,
               case.name AS case_name,
               'business_partner' AS conflict_type
        LIMIT 100
        """

        try:
            results = await self.neo4j_client.execute_query(
                query, {"company_id": str(company_id)}
            )

            conflicts = []
            for record in results:
                stake = record.get("stake", 0)
                conflicts.append(
                    {
                        "conflicting_id": record["conflicting_id"],
                        "case_id": record.get("case_id"),
                        "client_name": record.get("client_name", "Unknown"),
                        "client_id": record.get("client_id"),
                        "stake": stake,
                        "partner_name": record.get("partner_name", "Unknown"),
                        "conflict_type": "business_partner",
                        "description": f"Business partnership with adversary {record.get('partner_name', 'Unknown')} ({stake}% stake)",
                        "graph_path": {
                            "type": "business_partner",
                            "partner": record.get("partner_name"),
                            "stake": stake,
                            "client": record.get("client_name"),
                        },
                    }
                )

            return conflicts
        except Exception as e:
            logger.error(f"Error detecting business partners: {e}")
            return []

    async def detect_historical_conflicts(
        self, contact_id: UUID, years_back: int = 5
    ) -> List[Dict[str, Any]]:
        """Pattern 6: Past representations (5 years)."""
        cutoff_date = datetime.now() - timedelta(days=365 * years_back)

        query = """
        MATCH (contact {id: $contact_id})
        WHERE contact:Person OR contact:Company
        MATCH (contact)<-[r:REPRESENTED]-(lawyer:Lawyer)
        WHERE datetime(r.ended_at) > datetime($cutoff_date)
        MATCH (our_client)<-[:REPRESENTS]-(our_lawyer:Lawyer)
        WHERE our_client:Person OR our_client:Company
        MATCH (our_client)-[:OPPOSES]->(contact)
        MATCH (case:Case)-[:INVOLVES]->(our_client)
        WHERE case.status IN ['active', 'pending']
        RETURN DISTINCT contact.id AS conflicting_id,
               contact.name AS contact_name,
               r.ended_at AS last_representation,
               lawyer.name AS previous_lawyer,
               our_client.name AS client_name,
               our_client.id AS client_id,
               case.id AS case_id,
               case.name AS case_name,
               'historical_conflict' AS conflict_type
        LIMIT 100
        """

        try:
            results = await self.neo4j_client.execute_query(
                query,
                {"contact_id": str(contact_id), "cutoff_date": cutoff_date.isoformat()},
            )

            conflicts = []
            for record in results:
                last_rep = record.get("last_representation", "")
                conflicts.append(
                    {
                        "conflicting_id": record["conflicting_id"],
                        "case_id": record.get("case_id"),
                        "client_name": record.get("client_name", "Unknown"),
                        "client_id": record.get("client_id"),
                        "last_representation": last_rep,
                        "previous_lawyer": record.get("previous_lawyer", "Unknown"),
                        "conflict_type": "historical_conflict",
                        "description": f"Previously represented by {record.get('previous_lawyer', 'Unknown')} (ended {last_rep})",
                        "graph_path": {
                            "type": "historical_conflict",
                            "last_representation": last_rep,
                            "previous_lawyer": record.get("previous_lawyer"),
                            "client": record.get("client_name"),
                        },
                    }
                )

            return conflicts
        except Exception as e:
            logger.error(f"Error detecting historical conflicts: {e}")
            return []

    async def detect_group_conflicts(self, company_id: UUID) -> List[Dict[str, Any]]:
        """Pattern 7: Parent-subsidiary conflicts."""
        query = """
        MATCH path = (company:Company {id: $company_id})-[:SUBSIDIARY_OF*1..2]->(parent:Company)
        MATCH (our_client:Company)<-[:REPRESENTS]-(our_lawyer:Lawyer)
        MATCH (our_client)-[:OPPOSES]->(parent)
        MATCH (case:Case)-[:INVOLVES]->(our_client)
        WHERE case.status IN ['active', 'pending']
        RETURN DISTINCT parent.id AS conflicting_id,
               parent.name AS parent_name,
               [n IN nodes(path) | n.name] AS corporate_structure,
               length(path) AS depth,
               our_client.name AS client_name,
               our_client.id AS client_id,
               case.id AS case_id,
               case.name AS case_name,
               'group_company' AS conflict_type
        LIMIT 100
        """

        try:
            results = await self.neo4j_client.execute_query(
                query, {"company_id": str(company_id)}
            )

            conflicts = []
            for record in results:
                structure = record.get("corporate_structure", [])
                structure_str = " -> ".join(structure)

                conflicts.append(
                    {
                        "conflicting_id": record["conflicting_id"],
                        "case_id": record.get("case_id"),
                        "client_name": record.get("client_name", "Unknown"),
                        "client_id": record.get("client_id"),
                        "corporate_structure": structure,
                        "depth": record.get("depth", 0),
                        "conflict_type": "group_company",
                        "description": f"Group company conflict through corporate structure: {structure_str}",
                        "graph_path": {
                            "type": "group_company",
                            "structure": structure,
                            "depth": record.get("depth", 0),
                            "client": record.get("client_name"),
                        },
                    }
                )

            return conflicts
        except Exception as e:
            logger.error(f"Error detecting group conflicts: {e}")
            return []

    async def detect_professional_overlaps(
        self, contact_id: UUID
    ) -> List[Dict[str, Any]]:
        """Pattern 8: Shared accountants, notaries."""
        query = """
        MATCH (contact {id: $contact_id})
        WHERE contact:Person OR contact:Company
        MATCH (contact)-[:ADVISED_BY]->(advisor:Person)
        WHERE advisor.role IN ['accountant', 'notary', 'tax_advisor']
        MATCH (our_client)-[:ADVISED_BY]->(advisor)
        WHERE our_client:Person OR our_client:Company
        MATCH (our_client)<-[:REPRESENTS]-(our_lawyer:Lawyer)
        MATCH (our_client)-[:OPPOSES]->(contact)
        MATCH (case:Case)-[:INVOLVES]->(our_client)
        WHERE case.status IN ['active', 'pending']
        RETURN DISTINCT advisor.id AS advisor_id,
               advisor.name AS advisor_name,
               advisor.role AS advisor_type,
               contact.id AS conflicting_id,
               our_client.name AS client_name,
               our_client.id AS client_id,
               case.id AS case_id,
               case.name AS case_name,
               'professional_overlap' AS conflict_type
        LIMIT 100
        """

        try:
            results = await self.neo4j_client.execute_query(
                query, {"contact_id": str(contact_id)}
            )

            conflicts = []
            for record in results:
                conflicts.append(
                    {
                        "conflicting_id": record["conflicting_id"],
                        "case_id": record.get("case_id"),
                        "client_name": record.get("client_name", "Unknown"),
                        "client_id": record.get("client_id"),
                        "advisor_id": record.get("advisor_id"),
                        "advisor_name": record.get("advisor_name", "Unknown"),
                        "advisor_type": record.get("advisor_type", "professional"),
                        "conflict_type": "professional_overlap",
                        "description": f"Shared {record.get('advisor_type', 'professional')} {record.get('advisor_name', 'Unknown')} with adversary",
                        "graph_path": {
                            "type": "professional_overlap",
                            "advisor": record.get("advisor_name"),
                            "advisor_type": record.get("advisor_type"),
                            "client": record.get("client_name"),
                        },
                    }
                )

            return conflicts
        except Exception as e:
            logger.error(f"Error detecting professional overlaps: {e}")
            return []

    async def check_all_conflicts(
        self,
        contact_id: UUID,
        case_id: Optional[UUID] = None,
        contact_type: str = "contact",
    ) -> List[Dict[str, Any]]:
        """Run all 8 conflict detection patterns.

        Returns list of detected conflicts with severity scores.
        Performance target: < 500ms

        Args:
            contact_id: UUID of contact/company to check
            case_id: Optional case ID for context
            contact_type: Either "person" or "company" (determines which patterns to run)

        Returns:
            List of conflict dictionaries with severity scores
        """
        start_time = datetime.now()

        # Determine which detectors to run based on contact type
        tasks = []

        # Pattern 1: Direct conflicts (always run)
        tasks.append(self.detect_direct_conflicts(contact_id, case_id))

        # Pattern 4: Family ties (person only)
        if contact_type == "person":
            tasks.append(self.detect_family_ties(contact_id))

        # Pattern 6: Historical conflicts (always run)
        tasks.append(self.detect_historical_conflicts(contact_id))

        # Pattern 8: Professional overlaps (always run)
        tasks.append(self.detect_professional_overlaps(contact_id))

        # Company-specific patterns
        if contact_type == "company":
            tasks.append(self.detect_ownership_conflicts(contact_id))
            tasks.append(self.detect_director_overlap(contact_id))
            tasks.append(self.detect_business_partners(contact_id))
            tasks.append(self.detect_group_conflicts(contact_id))

        # Run all detectors in parallel
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error running conflict detection: {e}")
            return []

        # Combine results and filter out exceptions
        all_conflicts = []
        for result in results:
            if isinstance(result, list):
                all_conflicts.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Conflict detection task failed: {result}")

        # Calculate severity scores and enrich conflicts
        enriched_conflicts = []
        for conflict in all_conflicts:
            severity_score = self.calculate_conflict_score(conflict)
            conflict["severity_score"] = severity_score
            enriched_conflicts.append(conflict)

        # Sort by severity (highest first)
        enriched_conflicts.sort(key=lambda x: x["severity_score"], reverse=True)

        # Log performance
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            f"Conflict detection completed in {elapsed:.2f}ms. "
            f"Found {len(enriched_conflicts)} conflicts."
        )

        if elapsed > 500:
            logger.warning(f"Conflict detection exceeded 500ms target: {elapsed:.2f}ms")

        return enriched_conflicts

    def calculate_conflict_score(self, conflict_data: Dict[str, Any]) -> int:
        """Calculate severity score (0-100) based on conflict type.

        Args:
            conflict_data: Dictionary containing conflict details

        Returns:
            Integer severity score between 0-100
        """
        conflict_type = conflict_data.get("conflict_type", "unknown")

        # Base severity scores
        severity_map = {
            "direct_adversary": 100,  # CRITICAL
            "director_overlap": 90,  # VERY HIGH
            "family_tie": 85,  # VERY HIGH
            "indirect_ownership": 80,  # HIGH
            "group_company": 75,  # HIGH
            "business_partner": 70,  # HIGH
            "historical_conflict": 60,  # MEDIUM
            "professional_overlap": 50,  # MEDIUM
        }

        base_score = severity_map.get(conflict_type, 50)

        # Adjust for specific factors
        adjusted_score = base_score

        # Historical conflicts: reduce score based on time elapsed
        if conflict_type == "historical_conflict":
            last_rep = conflict_data.get("last_representation", "")
            if last_rep:
                try:
                    last_date = datetime.fromisoformat(last_rep.replace("Z", "+00:00"))
                    years_ago = (
                        datetime.now(last_date.tzinfo) - last_date
                    ).days / 365.25

                    # Reduce severity by 10 points per year
                    time_penalty = int(years_ago * 10)
                    adjusted_score = max(30, base_score - time_penalty)
                except Exception as e:
                    logger.debug(f"Error parsing date for historical conflict: {e}")

        # Indirect ownership: increase score for closer relationships
        elif conflict_type == "indirect_ownership":
            depth = conflict_data.get("ownership_depth", 3)
            # Closer relationships (depth 1) are more severe
            if depth == 1:
                adjusted_score = min(100, base_score + 10)
            elif depth == 2:
                adjusted_score = base_score
            else:  # depth 3
                adjusted_score = max(60, base_score - 10)

        # Business partners: increase score for higher stakes
        elif conflict_type == "business_partner":
            stake = conflict_data.get("stake", 0)
            if stake >= 50:  # Majority stake
                adjusted_score = min(100, base_score + 20)
            elif stake >= 40:
                adjusted_score = min(100, base_score + 10)

        # Family ties: adjust based on relationship closeness
        elif conflict_type == "family_tie":
            relationship = conflict_data.get("relationship_type", "unknown")
            if relationship in ["spouse", "parent", "child"]:
                adjusted_score = min(100, base_score + 10)  # Close family
            elif relationship == "sibling":
                adjusted_score = base_score
            else:
                adjusted_score = max(70, base_score - 5)  # Other relatives

        return min(100, max(0, adjusted_score))


# Singleton
_conflict_detector: Optional[ConflictDetector] = None
_lock = asyncio.Lock()


async def get_conflict_detector() -> ConflictDetector:
    """Get conflict detector singleton."""
    global _conflict_detector
    async with _lock:
        if _conflict_detector is None:
            _conflict_detector = ConflictDetector()
            await _conflict_detector.initialize()
        return _conflict_detector
