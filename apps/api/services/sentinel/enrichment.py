"""SENTINEL company enrichment service using BCE."""

import asyncio
import logging
from typing import Optional, Dict, List
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class BCEEnrichmentService:
    """Enrich company data from Belgian BCE database."""

    BASE_URL = "https://kbopub.economie.fgov.be/kbopub/api"  # Hypothetical endpoint

    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.cache: Dict[str, Dict] = {}  # Simple in-memory cache
        self.last_request_time: Optional[datetime] = None

    async def initialize(self):
        """Initialize HTTP client."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0), headers={"User-Agent": "LexiBel/1.0"}
        )

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()

    async def _rate_limit(self):
        """Enforce rate limiting (100 req/hour = 1 req/36s)."""
        if self.last_request_time:
            elapsed = (datetime.now() - self.last_request_time).total_seconds()
            if elapsed < 36:  # Wait to respect rate limit
                await asyncio.sleep(36 - elapsed)
        self.last_request_time = datetime.now()

    async def enrich_from_bce(self, bce_number: str) -> Optional[Dict]:
        """Get company data from BCE by BCE number.

        Args:
            bce_number: Belgian company number (10 digits, e.g., "0123456789")

        Returns:
            Company data dict or None if not found
        """
        # Normalize BCE number (remove dots, spaces)
        bce_clean = bce_number.replace(".", "").replace(" ", "").strip()

        if len(bce_clean) != 10 or not bce_clean.isdigit():
            logger.error(f"Invalid BCE number format: {bce_number}")
            return None

        # Check cache first
        if bce_clean in self.cache:
            logger.debug(f"BCE cache hit for {bce_clean}")
            return self.cache[bce_clean]

        # Rate limiting
        await self._rate_limit()

        try:
            # Since real BCE API requires specific setup, we'll mock for now
            # In production, this would be: response = await self.client.get(...)

            # MOCK DATA for demonstration (replace with real API call)
            mock_data = self._mock_bce_data(bce_clean)

            # Cache result (24 hours)
            self.cache[bce_clean] = mock_data

            logger.info(f"BCE enrichment successful for {bce_clean}")
            return mock_data

        except httpx.HTTPError as e:
            logger.error(f"BCE API error for {bce_clean}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error enriching {bce_clean}: {e}")
            return None

    def _mock_bce_data(self, bce_number: str) -> Dict:
        """Mock BCE data (replace with real API call in production)."""
        return {
            "bce_number": bce_number,
            "vat_number": f"BE{bce_number}",
            "legal_name": f"Company {bce_number[-4:]} SA",
            "legal_form": "SA",  # Société Anonyme
            "status": "active",
            "registration_date": "2010-01-15",
            "address": {
                "street": "Rue de la Loi 123",
                "postal_code": "1000",
                "city": "Brussels",
                "country": "Belgium",
            },
            "directors": [
                {"name": "Jean Dupont", "role": "CEO", "appointed_date": "2015-03-20"},
                {"name": "Marie Martin", "role": "CFO", "appointed_date": "2018-06-10"},
            ],
            "ubos": [  # Ultimate Beneficial Owners
                {"name": "Jean Dupont", "ownership_percent": 55.0},
                {"name": "Investment Fund Alpha", "ownership_percent": 45.0},
            ],
            "activity_codes": ["62010", "62020"],  # NACE-BEL codes
            "activity_description": "Computer programming activities",
            "employees_range": "10-49",
            "last_updated": datetime.now().isoformat(),
        }

    async def get_company_structure(self, bce_number: str) -> Optional[Dict]:
        """Get company ownership structure (UBOs, subsidiaries)."""
        data = await self.enrich_from_bce(bce_number)
        if not data:
            return None

        return {
            "bce_number": data["bce_number"],
            "legal_name": data["legal_name"],
            "ubos": data.get("ubos", []),
            "directors": data.get("directors", []),
            # In production, fetch subsidiaries via additional API calls
            "subsidiaries": [],  # TODO: Query for subsidiaries
            "parent_company": None,  # TODO: Query for parent
        }

    async def verify_bce_number(self, bce_number: str) -> bool:
        """Verify if BCE number is valid and active."""
        data = await self.enrich_from_bce(bce_number)
        return data is not None and data.get("status") == "active"

    async def search_by_name(self, company_name: str) -> List[Dict]:
        """Search companies by name (fuzzy search).

        Returns list of potential matches with BCE numbers.
        """
        # Rate limiting
        await self._rate_limit()

        # In production, call search API endpoint
        # For now, return mock results
        return [
            {
                "bce_number": "0123456789",
                "legal_name": company_name,
                "vat_number": "BE0123456789",
                "city": "Brussels",
                "match_score": 0.95,
            }
        ]


# Singleton
_bce_service: Optional[BCEEnrichmentService] = None
_lock = asyncio.Lock()


async def get_bce_service() -> BCEEnrichmentService:
    """Get BCE enrichment service singleton."""
    global _bce_service
    async with _lock:
        if _bce_service is None:
            _bce_service = BCEEnrichmentService()
            await _bce_service.initialize()
        return _bce_service
