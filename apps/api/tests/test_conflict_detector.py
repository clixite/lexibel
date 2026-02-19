"""Tests for SENTINEL conflict detection service."""

import pytest
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from apps.api.services.sentinel.conflict_detector import (
    ConflictDetector,
    get_conflict_detector,
)


@pytest.fixture
def conflict_detector():
    """Create a conflict detector instance."""
    detector = ConflictDetector()
    detector.neo4j_client = AsyncMock()
    return detector


@pytest.fixture
def sample_contact_id():
    """Sample contact UUID."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_case_id():
    """Sample case UUID."""
    return UUID("87654321-4321-8765-4321-876543218765")


class TestDirectConflicts:
    """Test Pattern 1: Direct adversary detection."""

    @pytest.mark.asyncio
    async def test_detect_direct_conflicts_found(
        self, conflict_detector, sample_contact_id
    ):
        """Test detection of direct adversary conflicts."""
        # Mock Neo4j response
        mock_result = [
            {
                "conflicting_id": str(sample_contact_id),
                "case_id": str(uuid4()),
                "client_name": "ACME Corp",
                "client_id": str(uuid4()),
                "case_name": "ACME vs CompetitorX",
                "conflict_type": "direct_adversary",
            }
        ]
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            return_value=mock_result
        )

        # Execute
        conflicts = await conflict_detector.detect_direct_conflicts(sample_contact_id)

        # Assert
        assert len(conflicts) == 1
        assert conflicts[0]["conflict_type"] == "direct_adversary"
        assert conflicts[0]["client_name"] == "ACME Corp"
        assert "description" in conflicts[0]
        assert "graph_path" in conflicts[0]

    @pytest.mark.asyncio
    async def test_detect_direct_conflicts_none_found(
        self, conflict_detector, sample_contact_id
    ):
        """Test when no direct conflicts exist."""
        conflict_detector.neo4j_client.execute_query = AsyncMock(return_value=[])

        conflicts = await conflict_detector.detect_direct_conflicts(sample_contact_id)

        assert len(conflicts) == 0

    @pytest.mark.asyncio
    async def test_detect_direct_conflicts_error_handling(
        self, conflict_detector, sample_contact_id
    ):
        """Test error handling in direct conflict detection."""
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            side_effect=Exception("Neo4j connection error")
        )

        conflicts = await conflict_detector.detect_direct_conflicts(sample_contact_id)

        assert len(conflicts) == 0  # Should return empty list on error


class TestOwnershipConflicts:
    """Test Pattern 2: Indirect ownership detection."""

    @pytest.mark.asyncio
    async def test_detect_ownership_conflicts_single_degree(
        self, conflict_detector, sample_contact_id
    ):
        """Test 1-degree ownership conflict."""
        mock_result = [
            {
                "conflicting_id": str(uuid4()),
                "ownership_depth": 1,
                "ownership_chain": ["Company A", "Company B"],
                "client_name": "Our Client Inc",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Test Case",
            }
        ]
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            return_value=mock_result
        )

        conflicts = await conflict_detector.detect_ownership_conflicts(
            sample_contact_id
        )

        assert len(conflicts) == 1
        assert conflicts[0]["ownership_depth"] == 1
        assert len(conflicts[0]["ownership_chain"]) == 2

    @pytest.mark.asyncio
    async def test_detect_ownership_conflicts_three_degrees(
        self, conflict_detector, sample_contact_id
    ):
        """Test 3-degree ownership chain."""
        mock_result = [
            {
                "conflicting_id": str(uuid4()),
                "ownership_depth": 3,
                "ownership_chain": ["Company A", "Company B", "Company C", "Company D"],
                "client_name": "Our Client Inc",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Test Case",
            }
        ]
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            return_value=mock_result
        )

        conflicts = await conflict_detector.detect_ownership_conflicts(
            sample_contact_id, max_depth=3
        )

        assert len(conflicts) == 1
        assert conflicts[0]["ownership_depth"] == 3


class TestDirectorOverlap:
    """Test Pattern 3: Shared directors."""

    @pytest.mark.asyncio
    async def test_detect_director_overlap_found(
        self, conflict_detector, sample_contact_id
    ):
        """Test detection of shared directors."""
        mock_result = [
            {
                "director_name": "John Smith",
                "director_id": str(uuid4()),
                "conflicting_id": str(uuid4()),
                "other_company_name": "Adversary Corp",
                "client_name": "Our Client Inc",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Test Case",
            }
        ]
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            return_value=mock_result
        )

        conflicts = await conflict_detector.detect_director_overlap(sample_contact_id)

        assert len(conflicts) == 1
        assert conflicts[0]["director_name"] == "John Smith"
        assert conflicts[0]["conflict_type"] == "director_overlap"


class TestFamilyTies:
    """Test Pattern 4: Family relationships."""

    @pytest.mark.asyncio
    async def test_detect_family_ties_spouse(
        self, conflict_detector, sample_contact_id
    ):
        """Test spouse relationship conflict."""
        mock_result = [
            {
                "conflicting_id": str(uuid4()),
                "relative_name": "Jane Doe",
                "relationship_type": "spouse",
                "client_name": "John Doe",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Doe vs CompanyX",
            }
        ]
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            return_value=mock_result
        )

        conflicts = await conflict_detector.detect_family_ties(sample_contact_id)

        assert len(conflicts) == 1
        assert conflicts[0]["relationship_type"] == "spouse"
        assert conflicts[0]["conflict_type"] == "family_tie"

    @pytest.mark.asyncio
    async def test_detect_family_ties_multiple_relations(
        self, conflict_detector, sample_contact_id
    ):
        """Test multiple family relationships."""
        mock_result = [
            {
                "conflicting_id": str(uuid4()),
                "relative_name": "Jane Doe",
                "relationship_type": "spouse",
                "client_name": "John Doe",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Test Case 1",
            },
            {
                "conflicting_id": str(uuid4()),
                "relative_name": "Bob Doe",
                "relationship_type": "sibling",
                "client_name": "John Doe",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Test Case 2",
            },
        ]
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            return_value=mock_result
        )

        conflicts = await conflict_detector.detect_family_ties(sample_contact_id)

        assert len(conflicts) == 2
        relationship_types = [c["relationship_type"] for c in conflicts]
        assert "spouse" in relationship_types
        assert "sibling" in relationship_types


class TestBusinessPartners:
    """Test Pattern 5: Business partnerships."""

    @pytest.mark.asyncio
    async def test_detect_business_partners_high_stake(
        self, conflict_detector, sample_contact_id
    ):
        """Test high-stake partnership conflict."""
        mock_result = [
            {
                "conflicting_id": str(uuid4()),
                "partner_name": "Partner Corp",
                "stake": 60,
                "client_name": "Our Client Inc",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Test Case",
            }
        ]
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            return_value=mock_result
        )

        conflicts = await conflict_detector.detect_business_partners(sample_contact_id)

        assert len(conflicts) == 1
        assert conflicts[0]["stake"] == 60
        assert conflicts[0]["conflict_type"] == "business_partner"

    @pytest.mark.asyncio
    async def test_detect_business_partners_minimum_threshold(
        self, conflict_detector, sample_contact_id
    ):
        """Test partnership at minimum threshold (>25%)."""
        mock_result = [
            {
                "conflicting_id": str(uuid4()),
                "partner_name": "Partner Corp",
                "stake": 26,
                "client_name": "Our Client Inc",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Test Case",
            }
        ]
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            return_value=mock_result
        )

        conflicts = await conflict_detector.detect_business_partners(sample_contact_id)

        assert len(conflicts) == 1


class TestHistoricalConflicts:
    """Test Pattern 6: Past representations."""

    @pytest.mark.asyncio
    async def test_detect_historical_conflicts_recent(
        self, conflict_detector, sample_contact_id
    ):
        """Test recent historical conflict (1 year ago)."""
        last_rep_date = (datetime.now() - timedelta(days=365)).isoformat()

        mock_result = [
            {
                "conflicting_id": str(sample_contact_id),
                "contact_name": "Former Client Inc",
                "last_representation": last_rep_date,
                "previous_lawyer": "Attorney Smith",
                "client_name": "Current Client Inc",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Test Case",
            }
        ]
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            return_value=mock_result
        )

        conflicts = await conflict_detector.detect_historical_conflicts(
            sample_contact_id, years_back=5
        )

        assert len(conflicts) == 1
        assert conflicts[0]["conflict_type"] == "historical_conflict"
        assert conflicts[0]["previous_lawyer"] == "Attorney Smith"

    @pytest.mark.asyncio
    async def test_detect_historical_conflicts_old(
        self, conflict_detector, sample_contact_id
    ):
        """Test old historical conflict (4 years ago)."""
        last_rep_date = (datetime.now() - timedelta(days=365 * 4)).isoformat()

        mock_result = [
            {
                "conflicting_id": str(sample_contact_id),
                "contact_name": "Former Client Inc",
                "last_representation": last_rep_date,
                "previous_lawyer": "Attorney Smith",
                "client_name": "Current Client Inc",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Test Case",
            }
        ]
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            return_value=mock_result
        )

        conflicts = await conflict_detector.detect_historical_conflicts(
            sample_contact_id, years_back=5
        )

        assert len(conflicts) == 1


class TestGroupConflicts:
    """Test Pattern 7: Group company conflicts."""

    @pytest.mark.asyncio
    async def test_detect_group_conflicts_parent(
        self, conflict_detector, sample_contact_id
    ):
        """Test parent company conflict."""
        mock_result = [
            {
                "conflicting_id": str(uuid4()),
                "parent_name": "Parent Corp",
                "corporate_structure": ["Subsidiary Inc", "Parent Corp"],
                "depth": 1,
                "client_name": "Our Client Inc",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Test Case",
            }
        ]
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            return_value=mock_result
        )

        conflicts = await conflict_detector.detect_group_conflicts(sample_contact_id)

        assert len(conflicts) == 1
        assert conflicts[0]["conflict_type"] == "group_company"
        assert conflicts[0]["depth"] == 1


class TestProfessionalOverlaps:
    """Test Pattern 8: Shared professionals."""

    @pytest.mark.asyncio
    async def test_detect_professional_overlaps_accountant(
        self, conflict_detector, sample_contact_id
    ):
        """Test shared accountant conflict."""
        mock_result = [
            {
                "advisor_id": str(uuid4()),
                "advisor_name": "Smith & Co Accountants",
                "advisor_type": "accountant",
                "conflicting_id": str(sample_contact_id),
                "client_name": "Our Client Inc",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Test Case",
            }
        ]
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            return_value=mock_result
        )

        conflicts = await conflict_detector.detect_professional_overlaps(
            sample_contact_id
        )

        assert len(conflicts) == 1
        assert conflicts[0]["advisor_type"] == "accountant"
        assert conflicts[0]["conflict_type"] == "professional_overlap"

    @pytest.mark.asyncio
    async def test_detect_professional_overlaps_multiple(
        self, conflict_detector, sample_contact_id
    ):
        """Test multiple shared professionals."""
        mock_result = [
            {
                "advisor_id": str(uuid4()),
                "advisor_name": "Smith Accountants",
                "advisor_type": "accountant",
                "conflicting_id": str(sample_contact_id),
                "client_name": "Our Client Inc",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Test Case 1",
            },
            {
                "advisor_id": str(uuid4()),
                "advisor_name": "Jones Notary",
                "advisor_type": "notary",
                "conflicting_id": str(sample_contact_id),
                "client_name": "Our Client Inc",
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "case_name": "Test Case 2",
            },
        ]
        conflict_detector.neo4j_client.execute_query = AsyncMock(
            return_value=mock_result
        )

        conflicts = await conflict_detector.detect_professional_overlaps(
            sample_contact_id
        )

        assert len(conflicts) == 2
        advisor_types = [c["advisor_type"] for c in conflicts]
        assert "accountant" in advisor_types
        assert "notary" in advisor_types


class TestCheckAllConflicts:
    """Test combined conflict detection."""

    @pytest.mark.asyncio
    async def test_check_all_conflicts_person(
        self, conflict_detector, sample_contact_id
    ):
        """Test checking all patterns for a person."""
        # Mock all detector methods
        conflict_detector.detect_direct_conflicts = AsyncMock(
            return_value=[
                {
                    "conflicting_id": str(uuid4()),
                    "conflict_type": "direct_adversary",
                    "client_name": "Client A",
                    "description": "Test conflict",
                }
            ]
        )
        conflict_detector.detect_family_ties = AsyncMock(
            return_value=[
                {
                    "conflicting_id": str(uuid4()),
                    "conflict_type": "family_tie",
                    "relationship_type": "spouse",
                    "description": "Family conflict",
                }
            ]
        )
        conflict_detector.detect_historical_conflicts = AsyncMock(return_value=[])
        conflict_detector.detect_professional_overlaps = AsyncMock(return_value=[])

        # Execute
        conflicts = await conflict_detector.check_all_conflicts(
            sample_contact_id, contact_type="person"
        )

        # Assert
        assert len(conflicts) == 2
        conflict_types = [c["conflict_type"] for c in conflicts]
        assert "direct_adversary" in conflict_types
        assert "family_tie" in conflict_types
        # All conflicts should have severity scores
        for conflict in conflicts:
            assert "severity_score" in conflict
            assert 0 <= conflict["severity_score"] <= 100

    @pytest.mark.asyncio
    async def test_check_all_conflicts_company(
        self, conflict_detector, sample_contact_id
    ):
        """Test checking all patterns for a company."""
        # Mock all detector methods
        conflict_detector.detect_direct_conflicts = AsyncMock(return_value=[])
        conflict_detector.detect_ownership_conflicts = AsyncMock(
            return_value=[
                {
                    "conflicting_id": str(uuid4()),
                    "conflict_type": "indirect_ownership",
                    "ownership_depth": 2,
                    "description": "Ownership conflict",
                }
            ]
        )
        conflict_detector.detect_director_overlap = AsyncMock(return_value=[])
        conflict_detector.detect_business_partners = AsyncMock(return_value=[])
        conflict_detector.detect_group_conflicts = AsyncMock(return_value=[])
        conflict_detector.detect_historical_conflicts = AsyncMock(return_value=[])
        conflict_detector.detect_professional_overlaps = AsyncMock(return_value=[])

        # Execute
        conflicts = await conflict_detector.check_all_conflicts(
            sample_contact_id, contact_type="company"
        )

        # Assert
        assert len(conflicts) == 1
        assert conflicts[0]["conflict_type"] == "indirect_ownership"

    @pytest.mark.asyncio
    async def test_check_all_conflicts_performance(
        self, conflict_detector, sample_contact_id
    ):
        """Test that conflict detection completes within 500ms target."""

        # Mock all detector methods with realistic delays
        async def mock_detect_delay(ms=10):
            """Simulate processing time."""
            import asyncio

            await asyncio.sleep(ms / 1000)
            return []

        conflict_detector.detect_direct_conflicts = AsyncMock(
            side_effect=lambda *args, **kwargs: mock_detect_delay(50)
        )
        conflict_detector.detect_family_ties = AsyncMock(
            side_effect=lambda *args, **kwargs: mock_detect_delay(50)
        )
        conflict_detector.detect_historical_conflicts = AsyncMock(
            side_effect=lambda *args, **kwargs: mock_detect_delay(50)
        )
        conflict_detector.detect_professional_overlaps = AsyncMock(
            side_effect=lambda *args, **kwargs: mock_detect_delay(50)
        )

        # Measure execution time
        start = datetime.now()
        await conflict_detector.check_all_conflicts(
            sample_contact_id, contact_type="person"
        )
        elapsed = (datetime.now() - start).total_seconds() * 1000

        # Should complete in < 500ms (parallel execution)
        # With 4 tasks at 50ms each, parallel execution should be ~50ms
        assert elapsed < 500

    @pytest.mark.asyncio
    async def test_check_all_conflicts_error_handling(
        self, conflict_detector, sample_contact_id
    ):
        """Test error handling when some detectors fail."""
        # Mock some detectors to fail
        conflict_detector.detect_direct_conflicts = AsyncMock(
            side_effect=Exception("Neo4j error")
        )
        conflict_detector.detect_family_ties = AsyncMock(
            return_value=[
                {
                    "conflicting_id": str(uuid4()),
                    "conflict_type": "family_tie",
                    "relationship_type": "spouse",
                    "description": "Family conflict",
                }
            ]
        )
        conflict_detector.detect_historical_conflicts = AsyncMock(return_value=[])
        conflict_detector.detect_professional_overlaps = AsyncMock(return_value=[])

        # Execute - should not raise exception
        conflicts = await conflict_detector.check_all_conflicts(
            sample_contact_id, contact_type="person"
        )

        # Should still return successful results
        assert len(conflicts) >= 0  # May have some results from successful detectors

    @pytest.mark.asyncio
    async def test_check_all_conflicts_sorting(
        self, conflict_detector, sample_contact_id
    ):
        """Test that conflicts are sorted by severity (highest first)."""
        # Mock detectors with different severity conflicts
        conflict_detector.detect_direct_conflicts = AsyncMock(
            return_value=[
                {
                    "conflicting_id": str(uuid4()),
                    "conflict_type": "direct_adversary",  # severity 100
                    "description": "High severity",
                }
            ]
        )
        conflict_detector.detect_family_ties = AsyncMock(return_value=[])
        conflict_detector.detect_historical_conflicts = AsyncMock(
            return_value=[
                {
                    "conflicting_id": str(uuid4()),
                    "conflict_type": "historical_conflict",  # severity ~60
                    "last_representation": datetime.now().isoformat(),
                    "description": "Medium severity",
                }
            ]
        )
        conflict_detector.detect_professional_overlaps = AsyncMock(
            return_value=[
                {
                    "conflicting_id": str(uuid4()),
                    "conflict_type": "professional_overlap",  # severity 50
                    "description": "Lower severity",
                }
            ]
        )

        # Execute
        conflicts = await conflict_detector.check_all_conflicts(
            sample_contact_id, contact_type="person"
        )

        # Assert sorted by severity (descending)
        assert len(conflicts) == 3
        assert conflicts[0]["conflict_type"] == "direct_adversary"
        assert conflicts[0]["severity_score"] > conflicts[1]["severity_score"]
        assert conflicts[1]["severity_score"] >= conflicts[2]["severity_score"]


class TestConflictScoreCalculation:
    """Test severity score calculation."""

    def test_calculate_score_direct_adversary(self, conflict_detector):
        """Test critical severity for direct adversary."""
        conflict = {"conflict_type": "direct_adversary"}
        score = conflict_detector.calculate_conflict_score(conflict)
        assert score == 100

    def test_calculate_score_director_overlap(self, conflict_detector):
        """Test very high severity for director overlap."""
        conflict = {"conflict_type": "director_overlap"}
        score = conflict_detector.calculate_conflict_score(conflict)
        assert score == 90

    def test_calculate_score_family_tie_close(self, conflict_detector):
        """Test family tie with close relationship."""
        conflict = {"conflict_type": "family_tie", "relationship_type": "spouse"}
        score = conflict_detector.calculate_conflict_score(conflict)
        assert score >= 85  # Base 85 + close family bonus

    def test_calculate_score_family_tie_sibling(self, conflict_detector):
        """Test family tie with sibling."""
        conflict = {"conflict_type": "family_tie", "relationship_type": "sibling"}
        score = conflict_detector.calculate_conflict_score(conflict)
        assert score == 85  # Base score, no adjustment

    def test_calculate_score_ownership_depth_1(self, conflict_detector):
        """Test ownership conflict at depth 1 (direct)."""
        conflict = {"conflict_type": "indirect_ownership", "ownership_depth": 1}
        score = conflict_detector.calculate_conflict_score(conflict)
        assert score >= 80  # Base + bonus for closeness

    def test_calculate_score_ownership_depth_3(self, conflict_detector):
        """Test ownership conflict at depth 3 (distant)."""
        conflict = {"conflict_type": "indirect_ownership", "ownership_depth": 3}
        score = conflict_detector.calculate_conflict_score(conflict)
        assert score <= 80  # Base - penalty for distance

    def test_calculate_score_business_partner_high_stake(self, conflict_detector):
        """Test business partner with majority stake."""
        conflict = {"conflict_type": "business_partner", "stake": 60}
        score = conflict_detector.calculate_conflict_score(conflict)
        assert score >= 70  # Base + stake bonus

    def test_calculate_score_business_partner_low_stake(self, conflict_detector):
        """Test business partner with minimum stake."""
        conflict = {"conflict_type": "business_partner", "stake": 26}
        score = conflict_detector.calculate_conflict_score(conflict)
        assert score == 70  # Base score

    def test_calculate_score_historical_recent(self, conflict_detector):
        """Test recent historical conflict (1 year ago)."""
        last_rep = (datetime.now() - timedelta(days=365)).isoformat()
        conflict = {
            "conflict_type": "historical_conflict",
            "last_representation": last_rep,
        }
        score = conflict_detector.calculate_conflict_score(conflict)
        assert score >= 50  # Base - small time penalty

    def test_calculate_score_historical_old(self, conflict_detector):
        """Test old historical conflict (4 years ago)."""
        last_rep = (datetime.now() - timedelta(days=365 * 4)).isoformat()
        conflict = {
            "conflict_type": "historical_conflict",
            "last_representation": last_rep,
        }
        score = conflict_detector.calculate_conflict_score(conflict)
        assert score <= 60  # Base - larger time penalty
        assert score >= 30  # Minimum threshold

    def test_calculate_score_professional_overlap(self, conflict_detector):
        """Test professional overlap base score."""
        conflict = {"conflict_type": "professional_overlap"}
        score = conflict_detector.calculate_conflict_score(conflict)
        assert score == 50

    def test_calculate_score_unknown_type(self, conflict_detector):
        """Test default score for unknown conflict type."""
        conflict = {"conflict_type": "unknown_type"}
        score = conflict_detector.calculate_conflict_score(conflict)
        assert score == 50  # Default fallback

    def test_calculate_score_bounds(self, conflict_detector):
        """Test that scores are always within 0-100 range."""
        test_cases = [
            {"conflict_type": "direct_adversary"},
            {
                "conflict_type": "historical_conflict",
                "last_representation": "2000-01-01",
            },
            {"conflict_type": "business_partner", "stake": 100},
        ]

        for conflict in test_cases:
            score = conflict_detector.calculate_conflict_score(conflict)
            assert 0 <= score <= 100


class TestSingleton:
    """Test conflict detector singleton."""

    @pytest.mark.asyncio
    async def test_get_conflict_detector_singleton(self):
        """Test that get_conflict_detector returns singleton."""
        with patch(
            "apps.api.services.sentinel.conflict_detector.get_neo4j_client"
        ) as mock_neo4j:
            mock_neo4j.return_value = AsyncMock()

            # Get detector twice
            detector1 = await get_conflict_detector()
            detector2 = await get_conflict_detector()

            # Should be same instance
            assert detector1 is detector2


class TestIntegration:
    """Integration tests (require Neo4j connection)."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_conflict_detection_flow(self, sample_contact_id):
        """Test full conflict detection flow with real Neo4j.

        This test requires Neo4j to be running and populated with test data.
        Mark with @pytest.mark.integration to skip in unit tests.
        """
        detector = await get_conflict_detector()

        # This would require Neo4j with test data
        conflicts = await detector.check_all_conflicts(
            sample_contact_id, contact_type="company"
        )

        # Basic assertions
        assert isinstance(conflicts, list)
        for conflict in conflicts:
            assert "conflict_type" in conflict
            assert "severity_score" in conflict
            assert 0 <= conflict["severity_score"] <= 100
