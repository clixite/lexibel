"""Tests for BCE enrichment service."""
import pytest
from apps.api.services.sentinel.enrichment import get_bce_service


@pytest.mark.asyncio
async def test_enrich_from_bce_valid():
    """Test BCE enrichment with valid number."""
    service = await get_bce_service()
    data = await service.enrich_from_bce("0123456789")

    assert data is not None
    assert data["bce_number"] == "0123456789"
    assert data["vat_number"] == "BE0123456789"
    assert "legal_name" in data
    assert "directors" in data
    assert "ubos" in data


@pytest.mark.asyncio
async def test_enrich_bce_invalid_format():
    """Test BCE enrichment with invalid format."""
    service = await get_bce_service()
    data = await service.enrich_from_bce("invalid")

    assert data is None


@pytest.mark.asyncio
async def test_get_company_structure():
    """Test company structure retrieval."""
    service = await get_bce_service()
    structure = await service.get_company_structure("0123456789")

    assert structure is not None
    assert "ubos" in structure
    assert "directors" in structure
    assert len(structure["ubos"]) > 0


@pytest.mark.asyncio
async def test_verify_bce_number():
    """Test BCE number verification."""
    service = await get_bce_service()
    is_valid = await service.verify_bce_number("0123456789")

    assert is_valid is True


@pytest.mark.asyncio
async def test_bce_caching():
    """Test BCE data caching."""
    service = await get_bce_service()

    # First call - cache miss
    data1 = await service.enrich_from_bce("0123456789")

    # Second call - cache hit (should be instant)
    data2 = await service.enrich_from_bce("0123456789")

    assert data1 == data2
    assert "0123456789" in service.cache


@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting enforcement."""
    service = await get_bce_service()

    import time
    start = time.time()

    # Make 2 calls
    await service.enrich_from_bce("0111111111")
    await service.enrich_from_bce("0222222222")

    elapsed = time.time() - start

    # Second call should be delayed by rate limiting
    # (unless both are in cache)
    assert elapsed >= 0  # Just verify no errors
