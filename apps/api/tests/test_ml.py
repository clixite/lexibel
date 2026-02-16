"""Tests for LXB-047-049: ML Pipeline — linkage, triage, deadlines."""
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from apps.api.services.ml.linkage_ranker import LinkageRanker
from apps.api.services.ml.email_triage import EmailTriageClassifier
from apps.api.services.ml.deadline_extractor import DeadlineExtractor
from apps.api.services.ml import MLPipeline
from apps.api.main import app


TENANT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


def _auth_headers() -> dict:
    return {
        "X-Tenant-ID": TENANT_ID,
        "X-User-ID": USER_ID,
        "X-User-Role": "super_admin",
        "X-User-Email": "test@lexibel.be",
    }


# ── Linkage Ranker tests ──


class TestLinkageRanker:
    def setup_method(self):
        self.ranker = LinkageRanker()

    def test_rank_by_reference(self):
        cases = [
            {"id": "1", "reference": "2026/001/A", "title": "Dupont c/ Martin", "contacts": []},
            {"id": "2", "reference": "2025/002", "title": "Other Case", "contacts": []},
        ]
        suggestions = self.ranker.rank(
            text="Concerne le dossier 2026/001/A",
            sender="avocat@test.be",
            existing_cases=cases,
        )
        assert len(suggestions) >= 1
        assert suggestions[0].case_id == "1"
        assert suggestions[0].confidence > 0.2

    def test_rank_by_contact(self):
        cases = [
            {"id": "1", "reference": "X", "title": "Case A", "contacts": ["jean@test.be"]},
            {"id": "2", "reference": "Y", "title": "Case B", "contacts": ["paul@test.be"]},
        ]
        suggestions = self.ranker.rank(
            text="Bonjour, voici les documents",
            sender="jean@test.be",
            existing_cases=cases,
        )
        assert len(suggestions) >= 1
        # Jean matches case 1
        case_ids = [s.case_id for s in suggestions]
        assert "1" in case_ids

    def test_rank_by_text_similarity(self):
        cases = [
            {"id": "1", "reference": "", "title": "Accident de la route Bruxelles", "contacts": [], "description": "Accident grave autoroute E40"},
            {"id": "2", "reference": "", "title": "Contrat de bail", "contacts": [], "description": "Litige bail commercial"},
        ]
        suggestions = self.ranker.rank(
            text="Accident autoroute E40 entre Bruxelles et Liège",
            sender="",
            existing_cases=cases,
        )
        assert len(suggestions) >= 1
        assert suggestions[0].case_id == "1"

    def test_rank_empty_text(self):
        suggestions = self.ranker.rank(text="", sender="", existing_cases=[{"id": "1"}])
        assert suggestions == []

    def test_rank_no_cases(self):
        suggestions = self.ranker.rank(text="test", sender="", existing_cases=[])
        assert suggestions == []

    def test_rank_top_k(self):
        ranker = LinkageRanker(top_k=2)
        cases = [
            {"id": str(i), "reference": f"REF-{i}", "title": f"Case {i}", "contacts": []}
            for i in range(10)
        ]
        suggestions = ranker.rank(
            text="REF-1 REF-2 REF-3 REF-4 REF-5",
            sender="",
            existing_cases=cases,
        )
        assert len(suggestions) <= 2


# ── Email Triage tests ──


class TestEmailTriage:
    def setup_method(self):
        self.classifier = EmailTriageClassifier()

    def test_classify_urgent(self):
        result = self.classifier.classify(
            subject="URGENT: Audience tribunal demain",
            body="Mise en demeure — délai expire ce vendredi. Citation à comparaître.",
            sender="greffe@just.fgov.be",
        )
        assert result.category == "URGENT"
        assert result.confidence > 0.3
        assert result.suggested_priority == 1

    def test_classify_normal(self):
        result = self.classifier.classify(
            subject="RE: Documents dossier Dupont",
            body="Veuillez trouver ci-joint les pièces demandées.",
            sender="avocat@test.be",
        )
        assert result.category == "NORMAL"
        assert result.suggested_priority == 3

    def test_classify_spam(self):
        result = self.classifier.classify(
            subject="Win a FREE trip! Click here",
            body="Congratulations! You won! Click here to claim your discount promo.",
            sender="noreply@spam.com",
        )
        assert result.category == "SPAM"
        assert result.suggested_priority == 5

    def test_classify_info_only(self):
        result = self.classifier.classify(
            subject="FYI: Mise à jour du système",
            body="Pour info, le rapport a été actualisé. Veuillez noter les modifications.",
            sender="admin@firm.be",
        )
        assert result.category == "INFO_ONLY"
        assert result.suggested_priority == 4

    def test_classify_professional_sender_boost(self):
        result = self.classifier.classify(
            subject="Communication",
            body="Audience fixée",
            sender="greffe@just.fgov.be",
        )
        # Professional sender should boost URGENT
        assert result.category in ("URGENT", "NORMAL")

    def test_classify_empty(self):
        result = self.classifier.classify(subject="", body="", sender="")
        assert result.category == "NORMAL"


# ── Deadline Extractor tests ──


class TestDeadlineExtractor:
    def setup_method(self):
        self.extractor = DeadlineExtractor()

    def test_extract_legal_deadline_appel(self):
        deadlines = self.extractor.extract(
            "Le délai d'appel est de 30 jours (Art. 1051 C.J.)",
            reference_date=date(2026, 3, 1),
        )
        assert len(deadlines) >= 1
        appel = [d for d in deadlines if d.deadline_type == "appel"]
        assert len(appel) >= 1
        assert appel[0].days == 30

    def test_extract_legal_deadline_cassation(self):
        deadlines = self.extractor.extract(
            "Pourvoi en cassation dans les 3 mois",
            reference_date=date(2026, 1, 1),
        )
        cassation = [d for d in deadlines if d.deadline_type == "cassation"]
        assert len(cassation) >= 1
        assert cassation[0].days == 90

    def test_extract_legal_deadline_citation(self):
        deadlines = self.extractor.extract(
            "Conformément à l'Art. 707 C.J., le délai de citation est de 8 jours.",
            reference_date=date(2026, 3, 1),
        )
        citation = [d for d in deadlines if d.deadline_type == "citation"]
        assert len(citation) >= 1
        assert citation[0].days == 8

    def test_extract_explicit_date_dmy(self):
        deadlines = self.extractor.extract(
            "L'audience est fixée pour le 15/03/2026.",
        )
        dates = [d for d in deadlines if "explicit" in d.deadline_type]
        assert len(dates) >= 1
        assert dates[0].date == "2026-03-15"

    def test_extract_explicit_date_french(self):
        deadlines = self.extractor.extract(
            "Avant le 15 mars 2026, veuillez déposer vos conclusions.",
        )
        dates = [d for d in deadlines if "explicit" in d.deadline_type]
        assert len(dates) >= 1
        assert dates[0].date == "2026-03-15"

    def test_extract_relative_deadline(self):
        deadlines = self.extractor.extract(
            "Vous disposez d'un délai de 15 jours pour répondre.",
            reference_date=date(2026, 3, 1),
        )
        relative = [d for d in deadlines if d.deadline_type == "relative"]
        assert len(relative) >= 1
        assert relative[0].days == 15

    def test_extract_relative_weeks(self):
        deadlines = self.extractor.extract(
            "Endéans les 2 semaines",
            reference_date=date(2026, 3, 1),
        )
        relative = [d for d in deadlines if d.deadline_type == "relative"]
        assert len(relative) >= 1
        assert relative[0].days == 14

    def test_extract_empty_text(self):
        deadlines = self.extractor.extract("")
        assert deadlines == []

    def test_business_day_adjustment(self):
        # March 1, 2026 is a Sunday in our test
        # Actually let's use a known date: 2026-03-07 is Saturday
        deadlines = self.extractor.extract(
            "Délai de citation de 8 jours",
            reference_date=date(2026, 2, 27),  # Friday
        )
        citation = [d for d in deadlines if d.deadline_type == "citation"]
        assert len(citation) >= 1
        # 2026-02-27 + 8 = 2026-03-07 (Saturday) -> adjusted to Monday 2026-03-09
        assert citation[0].date == "2026-03-09"

    def test_extract_opposition(self):
        deadlines = self.extractor.extract(
            "Il est possible de former opposition (Art. 1048 C.J.)",
        )
        opposition = [d for d in deadlines if d.deadline_type == "opposition"]
        assert len(opposition) >= 1

    def test_multiple_deadlines(self):
        text = """
        Le délai d'appel est de 30 jours. L'audience est fixée au 15/04/2026.
        Vous disposez d'un délai de 8 jours pour la citation.
        """
        deadlines = self.extractor.extract(text, reference_date=date(2026, 3, 1))
        assert len(deadlines) >= 3


# ── ML Pipeline tests ──


class TestMLPipeline:
    def setup_method(self):
        self.pipeline = MLPipeline()

    def test_process_event_full(self):
        event = {
            "subject": "URGENT: Audience tribunal 15 mars 2026",
            "body": "Concerne le dossier 2026/001/A. Délai d'appel de 30 jours.",
            "sender": "greffe@just.fgov.be",
            "existing_cases": [
                {"id": "1", "reference": "2026/001/A", "title": "Dupont", "contacts": []},
            ],
        }
        result = self.pipeline.process_event(event)

        # Classification
        assert result.classification is not None
        assert result.classification.category == "URGENT"

        # Case suggestions
        assert len(result.case_suggestions) >= 1
        assert result.case_suggestions[0].case_id == "1"

        # Deadlines
        assert len(result.deadlines) >= 1

    def test_process_event_no_cases(self):
        event = {
            "subject": "Test email",
            "body": "Some content about a deadline of 15 jours",
            "sender": "test@test.be",
        }
        result = self.pipeline.process_event(event)
        assert result.classification is not None
        assert result.case_suggestions == []

    def test_process_event_spam(self):
        event = {
            "subject": "WIN FREE STUFF Click here",
            "body": "Congratulations! Discount promo!",
            "sender": "noreply@spam.com",
        }
        result = self.pipeline.process_event(event)
        assert result.classification.category == "SPAM"


# ── ML API endpoint tests ──


class TestMLEndpoints:
    def test_classify_endpoint(self):
        client = TestClient(app)
        r = client.post(
            "/api/v1/ml/classify",
            json={
                "subject": "URGENT: Tribunal demain",
                "body": "Mise en demeure urgente",
                "sender": "greffe@just.fgov.be",
            },
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["category"] == "URGENT"
        assert "confidence" in data

    def test_link_endpoint(self):
        client = TestClient(app)
        r = client.post(
            "/api/v1/ml/link",
            json={
                "text": "Dossier 2026/001/A",
                "sender": "test@test.be",
                "existing_cases": [
                    {"id": "1", "reference": "2026/001/A", "title": "Test Case"},
                ],
            },
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["suggestions"]) >= 1

    def test_deadlines_endpoint(self):
        client = TestClient(app)
        r = client.post(
            "/api/v1/ml/deadlines",
            json={
                "text": "Le délai d'appel est de 30 jours (Art. 1051 C.J.). Audience le 15/03/2026.",
                "reference_date": "2026-03-01",
            },
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["deadlines"]) >= 2

    def test_process_endpoint(self):
        client = TestClient(app)
        r = client.post(
            "/api/v1/ml/process",
            json={
                "subject": "URGENT: Audience",
                "body": "Dossier 2026/001. Délai d'appel.",
                "sender": "greffe@just.fgov.be",
                "existing_cases": [
                    {"id": "1", "reference": "2026/001", "title": "Test"},
                ],
            },
            headers=_auth_headers(),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["classification"] is not None
        assert data["classification"]["category"] == "URGENT"
        assert len(data["suggestions"]) >= 1
        assert len(data["deadlines"]) >= 1

    def test_requires_auth(self):
        client = TestClient(app)
        r = client.post("/api/v1/ml/classify", json={"subject": "test"})
        assert r.status_code == 401
