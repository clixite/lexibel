"""Tests for AI agents: Due Diligence, Emotional Radar, Document Assembler, Agent Router."""

import uuid

import pytest

from apps.api.services.agents import AgentOrchestrator
from apps.api.services.agents.due_diligence_agent import DueDiligenceAgent
from apps.api.services.agents.emotional_radar import EmotionalRadar
from apps.api.services.agents.document_assembler import DocumentAssembler

TENANT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


def _auth_headers() -> dict:
    return {
        "X-Tenant-ID": TENANT_ID,
        "X-User-ID": USER_ID,
        "X-User-Role": "super_admin",
        "X-User-Email": "test@lexibel.be",
    }


# ── Due Diligence Agent ──


class TestDueDiligenceAgent:
    def setup_method(self):
        self.agent = DueDiligenceAgent()

    def test_empty_analysis(self):
        report = self.agent.analyze("case-001", "tenant-1")
        assert report.case_id == "case-001"
        assert report.overall_risk == "LOW"
        assert report.total_entities_checked == 0

    def test_entity_extraction_from_events(self):
        events = [
            {
                "id": "e1",
                "content": "Maître Dupont représente la SA Acme dans ce litige.",
            },
        ]
        report = self.agent.analyze("case-002", "tenant-1", events=events)
        assert report.total_entities_checked >= 1
        names = [e.entity_name for e in report.entities]
        assert any("Dupont" in n for n in names) or any("Acme" in n for n in names)

    def test_sanctions_hit_detection(self):
        events = [
            {
                "id": "e1",
                "content": "Maître Sanctioned Person a contacté le cabinet au sujet de Suspicious Corp SA.",
            },
        ]
        report = self.agent.analyze("case-003", "tenant-1", events=events)
        assert report.sanctions_hits >= 1
        assert report.overall_risk == "CRITICAL"

    def test_bce_dissolved_company(self):
        events = [
            {"id": "e1", "content": "La société Defunct SPRL est partie au litige."},
        ]
        report = self.agent.analyze("case-004", "tenant-1", events=events)
        dissolved = [e for e in report.entities if e.bce_status == "dissolved"]
        assert len(dissolved) >= 1

    def test_high_risk_keywords(self):
        report = self.agent.analyze(
            "case-005",
            "tenant-1",
            documents_text="Suspicion de blanchiment d'argent et fraude fiscale.",
        )
        assert len(report.risk_flags) >= 1
        assert any("HIGH" in f for f in report.risk_flags)

    def test_medium_risk_keywords(self):
        report = self.agent.analyze(
            "case-006",
            "tenant-1",
            documents_text="Le litige porte sur des factures impayées et une mise en demeure.",
        )
        flags = report.risk_flags
        assert any("MEDIUM" in f for f in flags)

    def test_recommendations_generated(self):
        events = [
            {
                "id": "e1",
                "content": "Maître Sanctioned Person a contacté le cabinet au sujet de Suspicious Corp SA.",
            },
        ]
        report = self.agent.analyze("case-007", "tenant-1", events=events)
        assert len(report.recommendations) >= 1
        assert any(
            "URGENT" in r or "sanction" in r.lower() for r in report.recommendations
        )

    def test_entity_deduplication(self):
        events = [
            {
                "id": "e1",
                "content": "Maître Dupont a envoyé un courrier. Me Dupont a confirmé.",
            },
        ]
        report = self.agent.analyze("case-008", "tenant-1", events=events)
        names = [e.entity_name.lower() for e in report.entities]
        # Should not have duplicates
        assert len(names) == len(set(names))

    def test_low_risk_clean_case(self):
        report = self.agent.analyze(
            "case-009",
            "tenant-1",
            documents_text="Contrat de bail résidentiel standard sans particularité.",
        )
        assert report.overall_risk == "LOW"


# ── Emotional Radar ──


class TestEmotionalRadar:
    def setup_method(self):
        self.radar = EmotionalRadar()

    def test_empty_events(self):
        profile = self.radar.analyze("case-001", "tenant-1", [])
        assert profile.overall_tone == "NEUTRAL"
        assert profile.overall_score == 0.0
        assert profile.trend == "STABLE"

    def test_cooperative_tone(self):
        events = [
            {
                "id": "e1",
                "type": "email",
                "date": "2026-01-01",
                "content": "Merci pour votre proposition. Je suis d'accord avec le compromis proposé.",
            },
        ]
        profile = self.radar.analyze("case-002", "tenant-1", events)
        assert profile.overall_score > 0
        assert profile.overall_tone == "COOPERATIVE"

    def test_hostile_tone(self):
        events = [
            {
                "id": "e1",
                "type": "email",
                "date": "2026-01-01",
                "content": "Votre incompétence est inacceptable. Faute grave de votre part. Nous exigeons réparation.",
            },
        ]
        profile = self.radar.analyze("case-003", "tenant-1", events)
        assert profile.overall_score < 0
        assert profile.overall_tone in ("HOSTILE", "THREATENING")

    def test_threatening_tone_flagged(self):
        events = [
            {
                "id": "e1",
                "type": "email",
                "date": "2026-01-01",
                "content": "Je vais porter plainte pénale et des poursuites pour harcèlement.",
            },
        ]
        profile = self.radar.analyze("case-004", "tenant-1", events)
        assert len(profile.flagged_events) >= 1
        assert profile.escalation_risk in ("HIGH", "CRITICAL")

    def test_trend_deteriorating(self):
        events = [
            {
                "id": "e1",
                "type": "email",
                "date": "2026-01-01",
                "content": "Merci pour votre accord et votre collaboration.",
            },
            {
                "id": "e2",
                "type": "email",
                "date": "2026-01-15",
                "content": "Merci, bien à vous, cordialement.",
            },
            {
                "id": "e3",
                "type": "email",
                "date": "2026-02-01",
                "content": "C'est inacceptable, je conteste cette décision.",
            },
            {
                "id": "e4",
                "type": "email",
                "date": "2026-02-15",
                "content": "Mise en demeure. Assignation devant le tribunal. Votre faute grave.",
            },
        ]
        profile = self.radar.analyze("case-005", "tenant-1", events)
        assert profile.trend == "DETERIORATING"

    def test_trend_improving(self):
        events = [
            {
                "id": "e1",
                "type": "email",
                "date": "2026-01-01",
                "content": "C'est inacceptable et incompétent.",
            },
            {
                "id": "e2",
                "type": "email",
                "date": "2026-01-15",
                "content": "Je conteste et désaccord total.",
            },
            {
                "id": "e3",
                "type": "email",
                "date": "2026-02-01",
                "content": "Merci pour votre proposition de compromis.",
            },
            {
                "id": "e4",
                "type": "email",
                "date": "2026-02-15",
                "content": "D'accord, accepté. Merci pour la collaboration.",
            },
        ]
        profile = self.radar.analyze("case-006", "tenant-1", events)
        assert profile.trend == "IMPROVING"

    def test_legal_threshold_detection(self):
        events = [
            {
                "id": "e1",
                "type": "email",
                "date": "2026-01-01",
                "content": "Ceci constitue du harcèlement et de la calomnie.",
            },
        ]
        profile = self.radar.analyze("case-007", "tenant-1", events)
        assert len(profile.flagged_events) >= 1
        flagged = profile.flagged_events[0]
        assert "Art." in flagged.flag_reason or "Code" in flagged.flag_reason

    def test_escalation_risk_critical(self):
        events = [
            {
                "id": "e1",
                "type": "email",
                "date": "2026-01-01",
                "content": "Menace de violence et harcèlement.",
            },
            {
                "id": "e2",
                "type": "email",
                "date": "2026-01-05",
                "content": "Poursuite pour diffamation et calomnie.",
            },
            {
                "id": "e3",
                "type": "email",
                "date": "2026-01-10",
                "content": "Menace de poursuites pénales.",
            },
        ]
        profile = self.radar.analyze("case-008", "tenant-1", events)
        assert profile.escalation_risk == "CRITICAL"

    def test_recommendations_for_high_risk(self):
        events = [
            {
                "id": "e1",
                "type": "email",
                "date": "2026-01-01",
                "content": "Menace de poursuites, je vais vous détruire.",
            },
        ]
        profile = self.radar.analyze("case-009", "tenant-1", events)
        assert len(profile.recommendations) >= 1

    def test_neutral_events_no_flags(self):
        events = [
            {
                "id": "e1",
                "type": "note",
                "date": "2026-01-01",
                "content": "Appel téléphonique pour fixer un rendez-vous.",
            },
        ]
        profile = self.radar.analyze("case-010", "tenant-1", events)
        assert len(profile.flagged_events) == 0
        assert profile.escalation_risk == "LOW"

    def test_skips_empty_content(self):
        events = [
            {"id": "e1", "type": "email", "date": "2026-01-01", "content": ""},
            {"id": "e2", "type": "email", "date": "2026-01-02", "body": "  "},
        ]
        profile = self.radar.analyze("case-011", "tenant-1", events)
        assert profile.events_analyzed == 0


# ── Document Assembler ──


class TestDocumentAssembler:
    def setup_method(self):
        self.assembler = DocumentAssembler()

    def test_list_templates(self):
        templates = self.assembler.list_templates()
        assert len(templates) == 4
        names = [t["id"] for t in templates]
        assert "mise_en_demeure" in names
        assert "conclusions" in names
        assert "requete_unilaterale" in names
        assert "citation" in names

    def test_get_template_info(self):
        info = self.assembler.get_template_info("mise_en_demeure")
        assert info is not None
        assert info["id"] == "mise_en_demeure"
        assert "sender_name" in info["required_variables"]

    def test_get_unknown_template(self):
        info = self.assembler.get_template_info("unknown")
        assert info is None

    def test_assemble_mise_en_demeure(self):
        doc = self.assembler.assemble(
            "mise_en_demeure",
            case_data={},
            variables={
                "sender_name": "Me Dupont",
                "sender_address": "Rue de la Loi 1, 1000 Bruxelles",
                "recipient_name": "M. Martin",
                "recipient_address": "Avenue Louise 100, 1050 Bruxelles",
                "facts": "Non-paiement de la facture n°2026-001.",
                "demand": "Paiement de la somme de 5.000 EUR.",
                "deadline_days": "15",
            },
        )
        assert doc.template_name == "mise_en_demeure"
        assert "Me Dupont" in doc.content
        assert "M. Martin" in doc.content
        assert "5.000 EUR" in doc.content
        assert "15 jours" in doc.content
        assert len(doc.missing_variables) == 0

    def test_assemble_with_missing_variables(self):
        doc = self.assembler.assemble(
            "mise_en_demeure",
            case_data={},
            variables={"sender_name": "Me Dupont"},
        )
        assert len(doc.missing_variables) > 0
        assert "recipient_name" in doc.missing_variables

    def test_assemble_conclusions(self):
        doc = self.assembler.assemble(
            "conclusions",
            case_data={},
            variables={
                "court_name": "Tribunal de première instance de Bruxelles",
                "case_number": "2026/1234/A",
                "plaintiff_name": "SA Acme",
                "defendant_name": "SPRL Beta",
                "facts": "Rupture de contrat commercial.",
                "legal_arguments": "Art. 1134 C.C. — force obligatoire des conventions.",
                "demands": "Condamner le défendeur au paiement de 50.000 EUR.",
            },
        )
        assert "Tribunal de première instance" in doc.content
        assert "SA Acme" in doc.content
        assert "PAR CES MOTIFS" in doc.content

    def test_assemble_unknown_template_raises(self):
        with pytest.raises(ValueError, match="Unknown template"):
            self.assembler.assemble("unknown", {}, {})

    def test_if_block_rendering(self):
        doc = self.assembler.assemble(
            "mise_en_demeure",
            case_data={},
            variables={
                "sender_name": "Me Dupont",
                "sender_address": "Bruxelles",
                "recipient_name": "M. Martin",
                "recipient_address": "Bruxelles",
                "facts": "Faits.",
                "demand": "Paiement.",
                "deadline_days": "15",
                "case_reference": "REF-2026-001",
                "legal_basis": "Art. 1382 C.C.",
            },
        )
        assert "REF-2026-001" in doc.content
        assert "Art. 1382 C.C." in doc.content

    def test_default_value_rendering(self):
        doc = self.assembler.assemble(
            "mise_en_demeure",
            case_data={},
            variables={
                "sender_name": "Me Dupont",
                "sender_address": "Bruxelles",
                "recipient_name": "M. Martin",
                "recipient_address": "Bruxelles",
                "facts": "Faits.",
                "demand": "Paiement.",
                "deadline_days": "15",
            },
        )
        # Default city should be Bruxelles
        assert "Bruxelles" in doc.content

    def test_assemble_requete_unilaterale(self):
        doc = self.assembler.assemble(
            "requete_unilaterale",
            case_data={},
            variables={
                "court_name": "Tribunal de commerce de Bruxelles",
                "requester_name": "SA Acme",
                "requester_address": "Rue du Commerce 1",
                "object": "Saisie conservatoire",
                "facts": "Le débiteur menace de déplacer ses actifs.",
                "legal_basis": "Art. 1413 C.J.",
                "demand": "Autoriser la saisie conservatoire.",
            },
        )
        assert "REQUÊTE UNILATÉRALE" in doc.content
        assert "SA Acme" in doc.content

    def test_assemble_citation(self):
        doc = self.assembler.assemble(
            "citation",
            case_data={},
            variables={
                "court_name": "Tribunal de première instance de Bruxelles",
                "plaintiff_name": "Me Dupont pour SA Acme",
                "defendant_name": "SPRL Beta",
                "defendant_address": "Rue de la Science 10, 1040 Bruxelles",
                "hearing_date": "15/03/2026",
                "object": "Recouvrement de créance",
                "facts": "Non-paiement de factures.",
                "demands": "Payer la somme de 25.000 EUR.",
            },
        )
        assert "CITATION À COMPARAÎTRE" in doc.content
        assert "15/03/2026" in doc.content
        assert "DONT ACTE" in doc.content


# ── Agent Orchestrator ──


class TestAgentOrchestrator:
    def setup_method(self):
        self.orchestrator = AgentOrchestrator()

    def test_run_due_diligence(self):
        report = self.orchestrator.run_due_diligence("case-1", "tenant-1")
        assert report.case_id == "case-1"

    def test_run_emotional_radar(self):
        events = [
            {
                "id": "e1",
                "type": "email",
                "date": "2026-01-01",
                "content": "Merci cordialement.",
            }
        ]
        profile = self.orchestrator.run_emotional_radar(
            "case-1", "tenant-1", events=events
        )
        assert profile.case_id == "case-1"
        assert profile.events_analyzed >= 1

    def test_assemble_document(self):
        doc = self.orchestrator.assemble_document(
            "mise_en_demeure",
            case_data={},
            variables={
                "sender_name": "Me X",
                "sender_address": "Bruxelles",
                "recipient_name": "M. Y",
                "recipient_address": "Bruxelles",
                "facts": "Faits.",
                "demand": "Paiement.",
                "deadline_days": "15",
            },
        )
        assert doc.template_name == "mise_en_demeure"
        assert "Me X" in doc.content

    def test_list_templates(self):
        templates = self.orchestrator.list_templates()
        assert len(templates) == 4


# ── Agent Router (API) ──


class TestAgentRouter:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from apps.api.main import app

        return TestClient(app)

    def test_run_due_diligence_endpoint(self, client):
        resp = client.post(
            "/api/v1/agents/due-diligence/case-001",
            json={"events": [], "documents_text": "Contrat standard."},
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == "case-001"
        assert "overall_risk" in data

    def test_run_emotional_radar_endpoint(self, client):
        resp = client.post(
            "/api/v1/agents/emotional-radar/case-002",
            json={
                "events": [
                    {
                        "id": "e1",
                        "type": "email",
                        "date": "2026-01-01",
                        "content": "Merci bien.",
                    }
                ]
            },
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == "case-002"
        assert "overall_tone" in data

    def test_assemble_document_endpoint(self, client):
        resp = client.post(
            "/api/v1/agents/assemble-document",
            json={
                "template_name": "mise_en_demeure",
                "case_data": {},
                "variables": {
                    "sender_name": "Me Test",
                    "sender_address": "Bruxelles",
                    "recipient_name": "M. Target",
                    "recipient_address": "Liège",
                    "facts": "Non-paiement.",
                    "demand": "Payer.",
                    "deadline_days": "15",
                },
            },
            headers=_auth_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "Me Test" in data["content"]
        assert data["template_name"] == "mise_en_demeure"

    def test_assemble_unknown_template_400(self, client):
        resp = client.post(
            "/api/v1/agents/assemble-document",
            json={"template_name": "nonexistent", "case_data": {}, "variables": {}},
            headers=_auth_headers(),
        )
        assert resp.status_code == 400

    def test_list_templates_endpoint(self, client):
        resp = client.get("/api/v1/agents/templates", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["templates"]) == 4

    def test_vllm_health_endpoint(self, client):
        resp = client.get("/api/v1/agents/vllm/health", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "unavailable")

    def test_lora_adapters_endpoint(self, client):
        resp = client.get("/api/v1/agents/lora/adapters", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 5
        assert any(a["name"] == "legal-fr" for a in data)
