"""Seed demo data for LexiBel - Production-ready test data.

This script creates a complete demo dataset for testing all features:
- 1 tenant (Cabinet Demo)
- 1 admin user
- 5 cases (various statuses and types)
- 10 contacts (5 natural, 5 legal with BCE)
- 20 timeline events
- 10 time entries
- 2 invoices
- 5 inbox items
- 3 call records (1 inbound answered 10min, 1 outbound answered 5min, 1 inbound missed)
- 2 transcriptions with realistic Belgian French legal dialogues (18 segments total)
- 5 email threads with 15 realistic messages
- 8 calendar events (2 past audiences, 2 future consultations, 1 today meeting, 1 deadline, 2 visio)
- 3 OAuth tokens (1 Google active, 1 Microsoft expired, 1 Google revoked)

Usage:
    python -m apps.api.scripts.seed_demo_data
"""

import asyncio
import sys
from datetime import datetime, timedelta, date
from pathlib import Path
from uuid import uuid4
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from packages.db.models import (
    Tenant,
    User,
    Case,
    Contact,
    CaseContact,
    InteractionEvent,
    InboxItem,
    TimeEntry,
    Invoice,
    InvoiceLine,
    ThirdPartyEntry,
    EmailThread,
    EmailMessage,
    CalendarEvent,
    CallRecord,
    Transcription,
    TranscriptionSegment,
    OAuthToken,
)

# Database URL from environment or default to production
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://lexibel:lexibel_dev_2026@localhost:5432/lexibel",
)


async def seed_data():
    """Seed demo data into the database."""

    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("🌱 Starting seed data...")

        # ── 1. Tenant ──
        print("\n📦 Creating/updating tenant...")
        from sqlalchemy import select, text

        # Check if tenant exists
        result = await session.execute(
            select(Tenant).where(Tenant.slug == "cabinet-demo")
        )
        tenant = result.scalar_one_or_none()

        if tenant:
            print(f"✅ Tenant already exists: {tenant.name} ({tenant.id})")
        else:
            tenant = Tenant(
                id=uuid4(),
                name="Cabinet Demo",
                slug="cabinet-demo",
                plan="professional",
                locale="fr-BE",
                config={"timezone": "Europe/Brussels", "currency": "EUR"},
                status="active",
            )
            session.add(tenant)
            await session.flush()
            print(f"✅ Tenant created: {tenant.name} ({tenant.id})")

        # Set tenant context for RLS
        await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant.id}'"))

        # ── 2. Admin User ──
        print("\n👤 Creating/updating admin user...")

        # Check if user exists
        result = await session.execute(
            select(User).where(User.email == "nicolas@clixite.be")
        )
        admin_user = result.scalar_one_or_none()

        # Generate a secure random password for demo data
        import secrets as _secrets

        from apps.api.auth.passwords import hash_password

        _demo_password = os.getenv("SEED_ADMIN_PASSWORD", "") or _secrets.token_urlsafe(
            16
        )

        if admin_user:
            # Update fields (password only updated if explicitly set via env var)
            if os.getenv("SEED_ADMIN_PASSWORD"):
                admin_user.hashed_password = hash_password(_demo_password)
            admin_user.full_name = "Nicolas Simon"
            admin_user.role = "partner"
            admin_user.hourly_rate_cents = 25000
            admin_user.is_active = True
            await session.flush()
            print(f"✅ User updated: {admin_user.email}")
        else:
            admin_user = User(
                id=uuid4(),
                tenant_id=tenant.id,
                email="nicolas@clixite.be",
                full_name="Nicolas Simon",
                role="partner",
                auth_provider="local",
                hashed_password=hash_password(_demo_password),
                mfa_enabled=False,
                hourly_rate_cents=25000,  # €250/h
                is_active=True,
            )
            session.add(admin_user)
            await session.flush()
            print(f"✅ User created: {admin_user.email}")
            if not os.getenv("SEED_ADMIN_PASSWORD"):
                print(f"   Generated temp password: {_demo_password}")

        # ── 3. Contacts ──
        print("\n📇 Creating 10 contacts...")
        contacts = []

        # Natural persons (5)
        natural_persons = [
            ("Jean Dupont", "jean.dupont@email.be", "+32470123456"),
            ("Marie Martin", "marie.martin@email.be", "+32471234567"),
            ("Pierre Dubois", "pierre.dubois@email.be", "+32472345678"),
            ("Sophie Laurent", "sophie.laurent@email.be", "+32473456789"),
            ("Luc Lefebvre", "luc.lefebvre@email.be", "+32474567890"),
        ]

        for name, email, phone in natural_persons:
            contact = Contact(
                id=uuid4(),
                tenant_id=tenant.id,
                type="natural",
                full_name=name,
                email=email,
                phone_e164=phone,
                language="fr",
                address={
                    "street": "Rue Example 123",
                    "city": "Bruxelles",
                    "zip": "1000",
                    "country": "BE",
                },
            )
            contacts.append(contact)
            session.add(contact)

        # Legal persons (5) with BCE numbers
        legal_persons = [
            ("SA Immobel", "0417.497.106", "contact@immobel.be"),
            ("SPRL TechStart", "0123.456.789", "info@techstart.be"),
            ("ASBL Culture Plus", "0987.654.321", "contact@cultureplus.be"),
            ("SCS Invest Group", "0555.123.456", "info@investgroup.be"),
            ("SC Avocats Associés", "0666.789.012", "cabinet@avocats.be"),
        ]

        for name, bce, email in legal_persons:
            contact = Contact(
                id=uuid4(),
                tenant_id=tenant.id,
                type="legal",
                full_name=name,
                bce_number=bce,
                email=email,
                language="fr",
                address={
                    "street": "Avenue Louise 250",
                    "city": "Bruxelles",
                    "zip": "1050",
                    "country": "BE",
                },
            )
            contacts.append(contact)
            session.add(contact)

        await session.flush()
        print(f"✅ {len(contacts)} contacts created")

        # ── 4. Cases ──
        print("\n📂 Creating 5 cases...")
        cases = []
        case_data = [
            (
                "2026/001",
                "Dupont c/ Immobel - Dommages et intérêts",
                "civil",
                "open",
                "Tribunal de première instance de Bruxelles",
            ),
            (
                "2026/002",
                "Martin - Divorce par consentement mutuel",
                "family",
                "in_progress",
                "Tribunal de la famille de Bruxelles",
            ),
            (
                "2026/003",
                "TechStart SPRL - Recouvrement créances",
                "commercial",
                "pending",
                None,
            ),
            (
                "2026/004",
                "Dubois - Licenciement abusif",
                "social",
                "in_progress",
                "Tribunal du travail de Bruxelles",
            ),
            (
                "2026/005",
                "Invest Group - Contrôle fiscal TVA",
                "fiscal",
                "closed",
                None,
            ),
        ]

        for ref, title, matter_type, status, jurisdiction in case_data:
            case = Case(
                id=uuid4(),
                tenant_id=tenant.id,
                reference=ref,
                title=title,
                matter_type=matter_type,
                status=status,
                jurisdiction=jurisdiction,
                responsible_user_id=admin_user.id,
                opened_at=date.today() - timedelta(days=30),
                closed_at=date.today() - timedelta(days=5)
                if status == "closed"
                else None,
                metadata_={"tags": ["demo"], "priority": "medium"},
            )
            cases.append(case)
            session.add(case)

        await session.flush()
        print(f"✅ {len(cases)} cases created")

        # ── 5. Case-Contact Links ──
        print("\n🔗 Linking contacts to cases...")
        case_contacts = [
            (cases[0], contacts[0], "client"),
            (cases[0], contacts[5], "adverse"),
            (cases[1], contacts[1], "client"),
            (cases[2], contacts[6], "client"),
            (cases[3], contacts[2], "client"),
            (cases[4], contacts[7], "client"),
        ]

        for case, contact, role in case_contacts:
            case_contact = CaseContact(
                tenant_id=tenant.id,
                case_id=case.id,
                contact_id=contact.id,
                role=role,
            )
            session.add(case_contact)

        await session.flush()
        print(f"✅ {len(case_contacts)} case-contact links created")

        # ── 6. Timeline Events ──
        print("\n📅 Creating 20 timeline events...")
        event_templates = [
            (
                "EMAIL",
                "📧 Email reçu de {contact}",
                "Le client a envoyé un email concernant le dossier.",
            ),
            (
                "CALL",
                "📞 Appel téléphonique avec {contact}",
                "Discussion téléphonique de 15 minutes.",
            ),
            ("MEETING", "🤝 Réunion avec {contact}", "Réunion au cabinet, durée 1h30."),
            (
                "DPA",
                "⚖️ Dépôt JBox - Nouvelle communication",
                "Communication judiciaire reçue via e-Deposit.",
            ),
            (
                "MANUAL",
                "📝 Note interne",
                "Avancement du dossier et prochaines étapes.",
            ),
        ]

        for i in range(20):
            case = cases[i % len(cases)]
            event_type, title_template, body = event_templates[i % len(event_templates)]

            # Use a contact name if available
            contact_name = contacts[i % len(contacts)].full_name
            title = title_template.format(contact=contact_name)

            event = InteractionEvent(
                id=uuid4(),
                tenant_id=tenant.id,
                case_id=case.id,
                source=event_type,
                event_type=event_type,
                title=title,
                body=body,
                occurred_at=datetime.now() - timedelta(days=20 - i),
                created_by=admin_user.id,
                metadata_={"source_id": f"demo-event-{i}"},
            )
            session.add(event)

        await session.flush()
        print("✅ 20 timeline events created")

        # ── 7. Time Entries ──
        print("\n⏱️  Creating 10 time entries...")
        time_entries = []

        for i in range(10):
            case = cases[i % len(cases)]
            status_choices = ["draft", "submitted", "approved", "invoiced"]
            status = status_choices[i % len(status_choices)]

            entry = TimeEntry(
                id=uuid4(),
                tenant_id=tenant.id,
                case_id=case.id,
                user_id=admin_user.id,
                date=date.today() - timedelta(days=10 - i),
                description=f"Travail sur dossier {case.reference} - Phase {i + 1}",
                duration_minutes=90 + (i * 15),  # 90 to 225 minutes
                hourly_rate_cents=25000,
                status=status,
            )
            time_entries.append(entry)
            session.add(entry)

        await session.flush()
        print(f"✅ {len(time_entries)} time entries created")

        # ── 8. Invoices ──
        print("\n💰 Creating 2 invoices...")

        # Invoice 1: Draft
        invoice1 = Invoice(
            id=uuid4(),
            tenant_id=tenant.id,
            case_id=cases[0].id,
            client_contact_id=contacts[0].id,  # Jean Dupont
            invoice_number="2026/001",
            issue_date=date.today() - timedelta(days=7),
            due_date=date.today() + timedelta(days=23),
            status="draft",
            subtotal_cents=62500,  # €625
            vat_rate=21.0,
            vat_amount_cents=13125,  # €131.25
            total_cents=75625,  # €756.25
        )
        session.add(invoice1)

        # Add invoice lines
        line1 = InvoiceLine(
            id=uuid4(),
            tenant_id=tenant.id,
            invoice_id=invoice1.id,
            description="Prestations juridiques - Janvier 2026",
            quantity=2.5,
            unit_price_cents=25000,
            total_cents=62500,
        )
        session.add(line1)

        # Invoice 2: Sent
        invoice2 = Invoice(
            id=uuid4(),
            tenant_id=tenant.id,
            case_id=cases[1].id,
            client_contact_id=contacts[1].id,  # Marie Martin
            invoice_number="2026/002",
            issue_date=date.today() - timedelta(days=15),
            due_date=date.today() + timedelta(days=15),
            status="sent",
            subtotal_cents=100000,  # €1000
            vat_rate=21.0,
            vat_amount_cents=21000,  # €210
            total_cents=121000,  # €1210
        )
        session.add(invoice2)

        line2 = InvoiceLine(
            id=uuid4(),
            tenant_id=tenant.id,
            invoice_id=invoice2.id,
            description="Honoraires - Divorce",
            quantity=4.0,
            unit_price_cents=25000,
            total_cents=100000,
        )
        session.add(line2)

        # Invoice 3: Paid
        invoice3 = Invoice(
            id=uuid4(),
            tenant_id=tenant.id,
            case_id=cases[2].id,
            client_contact_id=contacts[2].id,  # Pierre Dubois
            invoice_number="2026/003",
            issue_date=date.today() - timedelta(days=45),
            due_date=date.today() - timedelta(days=15),
            status="paid",
            subtotal_cents=150000,  # €1500
            vat_rate=21.0,
            vat_amount_cents=31500,  # €315
            total_cents=181500,  # €1815
        )
        session.add(invoice3)

        line3 = InvoiceLine(
            id=uuid4(),
            tenant_id=tenant.id,
            invoice_id=invoice3.id,
            description="Honoraires - Recouvrement créances - Phase 1",
            quantity=6.0,
            unit_price_cents=25000,
            total_cents=150000,
        )
        session.add(line3)

        await session.flush()
        print("✅ 3 invoices with lines created")

        # ── 9. Third-Party Entries ──
        print("\n💳 Creating third-party ledger entries...")

        tp1 = ThirdPartyEntry(
            id=uuid4(),
            tenant_id=tenant.id,
            case_id=cases[0].id,
            entry_date=date.today() - timedelta(days=10),
            description="Frais d'huissier - Signification",
            amount_cents=15000,  # €150
            entry_type="withdrawal",
            reference="HUIS-2026-001",
            created_by=admin_user.id,
        )
        session.add(tp1)

        tp2 = ThirdPartyEntry(
            id=uuid4(),
            tenant_id=tenant.id,
            case_id=cases[0].id,
            entry_date=date.today() - timedelta(days=5),
            description="Paiement client",
            amount_cents=15000,
            entry_type="deposit",
            reference="VIREMENT-2026-001",
            created_by=admin_user.id,
        )
        session.add(tp2)

        await session.flush()
        print("✅ Third-party entries created")

        # ── 10. Inbox Items ──
        print("\n📥 Creating 5 inbox items...")
        inbox_items_data = [
            ("OUTLOOK", "DRAFT", None, None),
            ("RINGOVER", "DRAFT", None, None),
            ("PLAUD", "DRAFT", None, None),
            ("OUTLOOK", "VALIDATED", cases[0].id, 0.95),
            ("DPA_JBOX", "REFUSED", None, None),
        ]

        for i, (source, status, suggested_case, confidence) in enumerate(
            inbox_items_data
        ):
            item = InboxItem(
                id=uuid4(),
                tenant_id=tenant.id,
                source=source,
                status=status,
                raw_payload={
                    "id": f"external-{source.lower()}-{i + 1}",
                    "from": f"sender{i + 1}@example.com",
                    "subject": f"Sujet #{i + 1}",
                    "body": f"Contenu de l'item #{i + 1} en attente de validation...",
                    "received_at": str(datetime.now() - timedelta(days=i)),
                },
                suggested_case_id=suggested_case,
                confidence=confidence,
                validated_by=admin_user.id if status == "VALIDATED" else None,
                validated_at=datetime.now() - timedelta(hours=i)
                if status == "VALIDATED"
                else None,
            )
            session.add(item)

        await session.flush()
        print("✅ 5 inbox items created")

        # ── 11. Email Threads & Messages ──
        print("\n📧 Creating 5 email threads with messages...")
        thread_count = 0
        message_count = 0

        try:
            # Thread 1: Demande de rendez-vous (3 messages, provider='google')
            thread1 = EmailThread(
                id=uuid4(),
                tenant_id=tenant.id,
                case_id=None,  # Pas encore lié à un dossier
                external_id=f"google-thread-{uuid4()}",
                provider="google",
                subject="Demande de rendez-vous - Litige commercial",
                participants={
                    "from": {
                        "email": "pierre.dubois@email.be",
                        "name": "Pierre Dubois",
                    },
                    "to": [{"email": admin_user.email, "name": admin_user.full_name}],
                },
                message_count=3,
                has_attachments=False,
                last_message_at=datetime.now() - timedelta(hours=2),
            )
            session.add(thread1)
            await session.flush()
            thread_count += 1

            # Messages Thread 1
            msg1_1 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread1.id,
                external_id=f"google-msg-{uuid4()}",
                provider="google",
                subject="Demande de rendez-vous - Litige commercial",
                from_address="pierre.dubois@email.be",
                to_addresses=[
                    {"email": admin_user.email, "name": admin_user.full_name}
                ],
                body_text="Bonjour Maître,\n\nJe souhaiterais prendre rendez-vous avec vous concernant un litige commercial avec un de mes fournisseurs. Seriez-vous disponible cette semaine?\n\nBien cordialement,\nPierre Dubois",
                body_html="<p>Bonjour Maître,</p><p>Je souhaiterais prendre rendez-vous avec vous concernant un litige commercial avec un de mes fournisseurs. Seriez-vous disponible cette semaine?</p><p>Bien cordialement,<br>Pierre Dubois</p>",
                is_read=True,
                received_at=datetime.now() - timedelta(days=1, hours=10),
            )
            session.add(msg1_1)
            message_count += 1

            msg1_2 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread1.id,
                external_id=f"google-msg-{uuid4()}",
                provider="google",
                subject="RE: Demande de rendez-vous - Litige commercial",
                from_address=admin_user.email,
                to_addresses=[
                    {"email": "pierre.dubois@email.be", "name": "Pierre Dubois"}
                ],
                body_text="Bonjour Monsieur Dubois,\n\nJe peux vous recevoir jeudi à 14h ou vendredi à 10h. Qu'en pensez-vous?\n\nCordialement,\nMaître Nicolas Simon",
                body_html="<p>Bonjour Monsieur Dubois,</p><p>Je peux vous recevoir jeudi à 14h ou vendredi à 10h. Qu'en pensez-vous?</p><p>Cordialement,<br>Maître Nicolas Simon</p>",
                is_read=True,
                received_at=datetime.now() - timedelta(days=1, hours=8),
            )
            session.add(msg1_2)
            message_count += 1

            msg1_3 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread1.id,
                external_id=f"google-msg-{uuid4()}",
                provider="google",
                subject="RE: Demande de rendez-vous - Litige commercial",
                from_address="pierre.dubois@email.be",
                to_addresses=[
                    {"email": admin_user.email, "name": admin_user.full_name}
                ],
                body_text="Parfait, jeudi à 14h me convient. À jeudi!\n\nPierre",
                body_html="<p>Parfait, jeudi à 14h me convient. À jeudi!</p><p>Pierre</p>",
                is_read=False,
                is_important=False,
                received_at=datetime.now() - timedelta(hours=2),
            )
            session.add(msg1_3)
            message_count += 1

            # Thread 2: Documents manquants (2 messages, outlook, attachments)
            thread2 = EmailThread(
                id=uuid4(),
                tenant_id=tenant.id,
                case_id=cases[0].id,  # Dupont c/ Immobel
                external_id=f"outlook-thread-{uuid4()}",
                provider="outlook",
                subject="Documents manquants - Dossier 2026/001",
                participants={
                    "from": {"email": "jean.dupont@email.be", "name": "Jean Dupont"},
                    "to": [{"email": admin_user.email, "name": admin_user.full_name}],
                },
                message_count=2,
                has_attachments=True,
                last_message_at=datetime.now() - timedelta(days=1, hours=5),
            )
            session.add(thread2)
            await session.flush()
            thread_count += 1

            msg2_1 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread2.id,
                external_id=f"outlook-msg-{uuid4()}",
                provider="outlook",
                subject="Documents manquants - Dossier 2026/001",
                from_address="jean.dupont@email.be",
                to_addresses=[
                    {"email": admin_user.email, "name": admin_user.full_name}
                ],
                body_text="Bonjour Maître,\n\nVoici les documents que vous m'aviez demandés: le rapport d'expertise et les photos des dommages.\n\nCordialement,\nJean Dupont",
                body_html="<p>Bonjour Maître,</p><p>Voici les documents que vous m'aviez demandés: le rapport d'expertise et les photos des dommages.</p><p>Cordialement,<br>Jean Dupont</p>",
                is_read=True,
                has_attachments=True,
                attachments=[
                    {
                        "filename": "rapport_expertise_immobel.pdf",
                        "size_bytes": 2458621,
                        "mime_type": "application/pdf",
                    },
                    {
                        "filename": "photos_dommages.zip",
                        "size_bytes": 8945123,
                        "mime_type": "application/zip",
                    },
                ],
                received_at=datetime.now() - timedelta(days=1, hours=8),
            )
            session.add(msg2_1)
            message_count += 1

            msg2_2 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread2.id,
                external_id=f"outlook-msg-{uuid4()}",
                provider="outlook",
                subject="RE: Documents manquants - Dossier 2026/001",
                from_address=admin_user.email,
                to_addresses=[{"email": "jean.dupont@email.be", "name": "Jean Dupont"}],
                body_text="Merci Jean, j'ai bien reçu les documents. Je les examine et reviens vers vous rapidement.\n\nMaître Simon",
                body_html="<p>Merci Jean, j'ai bien reçu les documents. Je les examine et reviens vers vous rapidement.</p><p>Maître Simon</p>",
                is_read=True,
                received_at=datetime.now() - timedelta(days=1, hours=5),
            )
            session.add(msg2_2)
            message_count += 1

            # Thread 3: Question honoraires (4 messages)
            thread3 = EmailThread(
                id=uuid4(),
                tenant_id=tenant.id,
                case_id=cases[1].id,  # Martin - Divorce
                external_id=f"google-thread-{uuid4()}",
                provider="google",
                subject="Question sur vos honoraires",
                participants={
                    "from": {"email": "marie.martin@email.be", "name": "Marie Martin"},
                    "to": [{"email": admin_user.email, "name": admin_user.full_name}],
                },
                message_count=4,
                has_attachments=False,
                last_message_at=datetime.now() - timedelta(hours=18),
            )
            session.add(thread3)
            await session.flush()
            thread_count += 1

            msg3_1 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread3.id,
                external_id=f"google-msg-{uuid4()}",
                provider="google",
                subject="Question sur vos honoraires",
                from_address="marie.martin@email.be",
                to_addresses=[
                    {"email": admin_user.email, "name": admin_user.full_name}
                ],
                body_text="Bonjour Maître,\n\nPourriez-vous me donner une estimation des honoraires pour notre divorce par consentement mutuel?\n\nMerci,\nMarie Martin",
                body_html="<p>Bonjour Maître,</p><p>Pourriez-vous me donner une estimation des honoraires pour notre divorce par consentement mutuel?</p><p>Merci,<br>Marie Martin</p>",
                is_read=True,
                received_at=datetime.now() - timedelta(days=3, hours=14),
            )
            session.add(msg3_1)
            message_count += 1

            msg3_2 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread3.id,
                external_id=f"google-msg-{uuid4()}",
                provider="google",
                subject="RE: Question sur vos honoraires",
                from_address=admin_user.email,
                to_addresses=[
                    {"email": "marie.martin@email.be", "name": "Marie Martin"}
                ],
                body_text="Bonjour Madame Martin,\n\nPour un divorce par consentement mutuel, mes honoraires sont de 1.500€ HTVA. Cela inclut la rédaction de la convention, les démarches administratives et la représentation.\n\nCordialement,\nMaître Simon",
                body_html="<p>Bonjour Madame Martin,</p><p>Pour un divorce par consentement mutuel, mes honoraires sont de 1.500€ HTVA. Cela inclut la rédaction de la convention, les démarches administratives et la représentation.</p><p>Cordialement,<br>Maître Simon</p>",
                is_read=True,
                received_at=datetime.now() - timedelta(days=3, hours=10),
            )
            session.add(msg3_2)
            message_count += 1

            msg3_3 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread3.id,
                external_id=f"google-msg-{uuid4()}",
                provider="google",
                subject="RE: Question sur vos honoraires",
                from_address="marie.martin@email.be",
                to_addresses=[
                    {"email": admin_user.email, "name": admin_user.full_name}
                ],
                body_text="Merci pour votre réponse. Cela me semble correct. Les frais de notaire sont en plus je suppose?\n\nMarie",
                body_html="<p>Merci pour votre réponse. Cela me semble correct. Les frais de notaire sont en plus je suppose?</p><p>Marie</p>",
                is_read=True,
                received_at=datetime.now() - timedelta(days=2, hours=16),
            )
            session.add(msg3_3)
            message_count += 1

            msg3_4 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread3.id,
                external_id=f"google-msg-{uuid4()}",
                provider="google",
                subject="RE: Question sur vos honoraires",
                from_address=admin_user.email,
                to_addresses=[
                    {"email": "marie.martin@email.be", "name": "Marie Martin"}
                ],
                body_text="Oui exactement, les frais de notaire pour le partage des biens sont distincts et à prévoir en plus (environ 1.000-1.500€).\n\nMaître Simon",
                body_html="<p>Oui exactement, les frais de notaire pour le partage des biens sont distincts et à prévoir en plus (environ 1.000-1.500€).</p><p>Maître Simon</p>",
                is_read=True,
                received_at=datetime.now() - timedelta(hours=18),
            )
            session.add(msg3_4)
            message_count += 1

            # Thread 4: Confirmation audience (2 messages, important)
            thread4 = EmailThread(
                id=uuid4(),
                tenant_id=tenant.id,
                case_id=cases[3].id,  # Dubois - Licenciement
                external_id=f"outlook-thread-{uuid4()}",
                provider="outlook",
                subject="URGENT - Confirmation audience Tribunal du Travail",
                participants={
                    "from": {
                        "email": "greffe.travail@just.fgov.be",
                        "name": "Greffe Tribunal du Travail",
                    },
                    "to": [{"email": admin_user.email, "name": admin_user.full_name}],
                },
                message_count=2,
                has_attachments=False,
                is_important=True,
                last_message_at=datetime.now() - timedelta(hours=4),
            )
            session.add(thread4)
            await session.flush()
            thread_count += 1

            msg4_1 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread4.id,
                external_id=f"outlook-msg-{uuid4()}",
                provider="outlook",
                subject="URGENT - Confirmation audience Tribunal du Travail",
                from_address="greffe.travail@just.fgov.be",
                to_addresses=[
                    {"email": admin_user.email, "name": admin_user.full_name}
                ],
                body_text="Maître,\n\nNous vous confirmons l'audience dans le dossier DUBOIS Pierre c/ ACME SPRL fixée au 28 février 2026 à 14h00, salle 3.\n\nVeuillez confirmer votre présence.\n\nLe Greffe",
                body_html="<p>Maître,</p><p>Nous vous confirmons l'audience dans le dossier <strong>DUBOIS Pierre c/ ACME SPRL</strong> fixée au <strong>28 février 2026 à 14h00</strong>, salle 3.</p><p>Veuillez confirmer votre présence.</p><p>Le Greffe</p>",
                is_read=True,
                is_important=True,
                received_at=datetime.now() - timedelta(hours=6),
            )
            session.add(msg4_1)
            message_count += 1

            msg4_2 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread4.id,
                external_id=f"outlook-msg-{uuid4()}",
                provider="outlook",
                subject="RE: URGENT - Confirmation audience Tribunal du Travail",
                from_address=admin_user.email,
                to_addresses=[
                    {
                        "email": "greffe.travail@just.fgov.be",
                        "name": "Greffe Tribunal du Travail",
                    }
                ],
                body_text="Madame, Monsieur,\n\nJe confirme ma présence à l'audience du 28 février 2026 à 14h00.\n\nCordialement,\nMaître Nicolas Simon",
                body_html="<p>Madame, Monsieur,</p><p>Je confirme ma présence à l'audience du 28 février 2026 à 14h00.</p><p>Cordialement,<br>Maître Nicolas Simon</p>",
                is_read=True,
                received_at=datetime.now() - timedelta(hours=4),
            )
            session.add(msg4_2)
            message_count += 1

            # Thread 5: Accusé réception contrat (4 messages)
            thread5 = EmailThread(
                id=uuid4(),
                tenant_id=tenant.id,
                case_id=cases[2].id,  # TechStart - Recouvrement
                external_id=f"google-thread-{uuid4()}",
                provider="google",
                subject="Accusé de réception - Mise en demeure",
                participants={
                    "from": {"email": "info@techstart.be", "name": "TechStart SPRL"},
                    "to": [{"email": admin_user.email, "name": admin_user.full_name}],
                },
                message_count=4,
                has_attachments=True,
                last_message_at=datetime.now() - timedelta(hours=12),
            )
            session.add(thread5)
            await session.flush()
            thread_count += 1

            msg5_1 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread5.id,
                external_id=f"google-msg-{uuid4()}",
                provider="google",
                subject="Accusé de réception - Mise en demeure",
                from_address="info@techstart.be",
                to_addresses=[
                    {"email": admin_user.email, "name": admin_user.full_name}
                ],
                body_text="Maître,\n\nNous avons bien reçu votre mise en demeure concernant notre créance.\n\nNous souhaitons trouver un arrangement.\n\nTechStart SPRL",
                body_html="<p>Maître,</p><p>Nous avons bien reçu votre mise en demeure concernant notre créance.</p><p>Nous souhaitons trouver un arrangement.</p><p>TechStart SPRL</p>",
                is_read=True,
                received_at=datetime.now() - timedelta(days=2, hours=9),
            )
            session.add(msg5_1)
            message_count += 1

            msg5_2 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread5.id,
                external_id=f"google-msg-{uuid4()}",
                provider="google",
                subject="RE: Accusé de réception - Mise en demeure",
                from_address=admin_user.email,
                to_addresses=[{"email": "info@techstart.be", "name": "TechStart SPRL"}],
                body_text="Bonjour,\n\nJe prends note de votre volonté de trouver un arrangement. Quelle est votre proposition?\n\nMaître Simon",
                body_html="<p>Bonjour,</p><p>Je prends note de votre volonté de trouver un arrangement. Quelle est votre proposition?</p><p>Maître Simon</p>",
                is_read=True,
                received_at=datetime.now() - timedelta(days=1, hours=14),
            )
            session.add(msg5_2)
            message_count += 1

            msg5_3 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread5.id,
                external_id=f"google-msg-{uuid4()}",
                provider="google",
                subject="RE: Accusé de réception - Mise en demeure",
                from_address="info@techstart.be",
                to_addresses=[
                    {"email": admin_user.email, "name": admin_user.full_name}
                ],
                body_text="Nous proposons un paiement en 3 échéances mensuelles de 5.000€, première échéance début mars.\n\nVeuillez trouver ci-joint notre proposition formelle.\n\nTechStart",
                body_html="<p>Nous proposons un paiement en 3 échéances mensuelles de 5.000€, première échéance début mars.</p><p>Veuillez trouver ci-joint notre proposition formelle.</p><p>TechStart</p>",
                is_read=True,
                has_attachments=True,
                attachments=[
                    {
                        "filename": "proposition_paiement_echelonne.pdf",
                        "size_bytes": 145678,
                        "mime_type": "application/pdf",
                    }
                ],
                received_at=datetime.now() - timedelta(days=1, hours=10),
            )
            session.add(msg5_3)
            message_count += 1

            msg5_4 = EmailMessage(
                id=uuid4(),
                tenant_id=tenant.id,
                thread_id=thread5.id,
                external_id=f"google-msg-{uuid4()}",
                provider="google",
                subject="RE: Accusé de réception - Mise en demeure",
                from_address=admin_user.email,
                to_addresses=[{"email": "info@techstart.be", "name": "TechStart SPRL"}],
                body_text="J'ai transmis votre proposition à mon client. Vous aurez une réponse sous 48h.\n\nMaître Simon",
                body_html="<p>J'ai transmis votre proposition à mon client. Vous aurez une réponse sous 48h.</p><p>Maître Simon</p>",
                is_read=True,
                received_at=datetime.now() - timedelta(hours=12),
            )
            session.add(msg5_4)
            message_count += 1

            await session.flush()
            print(
                f"✓ {thread_count} email threads with {message_count} messages created"
            )
        except Exception as e:
            print(f"✗ Error creating email threads: {e}")

        # ── 12. Calendar Events ──
        print("\n📅 Creating 8 calendar events...")
        calendar_count = 0

        try:
            # Event 1: Audience tribunal (past)
            event1 = CalendarEvent(
                id=uuid4(),
                tenant_id=tenant.id,
                user_id=admin_user.id,
                case_id=cases[0].id,  # Dupont c/ Immobel
                external_id=f"outlook-event-{uuid4()}",
                provider="outlook",
                title="Audience - Dupont c/ Immobel",
                description="Première audience devant le Tribunal de première instance. Dossier 2026/001. Objet: dommages et intérêts suite malfaçons.",
                start_time=datetime.now() - timedelta(days=15, hours=-14),
                end_time=datetime.now() - timedelta(days=15, hours=-16),
                location="Tribunal de première instance de Bruxelles - Salle 12",
                attendees=[
                    {
                        "email": admin_user.email,
                        "name": admin_user.full_name,
                        "response": "accepted",
                    },
                    {
                        "email": "jean.dupont@email.be",
                        "name": "Jean Dupont",
                        "response": "accepted",
                    },
                ],
                is_all_day=False,
                status="completed",
            )
            session.add(event1)
            calendar_count += 1

            # Event 2: Audience tribunal (past)
            event2 = CalendarEvent(
                id=uuid4(),
                tenant_id=tenant.id,
                user_id=admin_user.id,
                case_id=cases[3].id,  # Dubois - Licenciement
                external_id=f"google-event-{uuid4()}",
                provider="google",
                title="Audience - Dubois c/ ACME - Licenciement abusif",
                description="Comparution devant le Tribunal du travail. Dossier 2026/004.",
                start_time=datetime.now() - timedelta(days=8, hours=-14),
                end_time=datetime.now() - timedelta(days=8, hours=-16, minutes=-30),
                location="Tribunal du travail de Bruxelles - Salle 3",
                attendees=[
                    {
                        "email": admin_user.email,
                        "name": admin_user.full_name,
                        "response": "accepted",
                    },
                    {
                        "email": "pierre.dubois@email.be",
                        "name": "Pierre Dubois",
                        "response": "accepted",
                    },
                ],
                is_all_day=False,
                status="completed",
            )
            session.add(event2)
            calendar_count += 1

            # Event 3: Consultation client (future)
            event3 = CalendarEvent(
                id=uuid4(),
                tenant_id=tenant.id,
                user_id=admin_user.id,
                case_id=cases[1].id,  # Martin - Divorce
                external_id=f"outlook-event-{uuid4()}",
                provider="outlook",
                title="Consultation - Époux Martin",
                description="Rendez-vous avec M. et Mme Martin pour finaliser la convention de divorce. Prévoir 1h30.",
                start_time=datetime.now() + timedelta(days=5, hours=10),
                end_time=datetime.now() + timedelta(days=5, hours=11, minutes=30),
                location="Cabinet - Bureau Maître Simon",
                attendees=[
                    {
                        "email": admin_user.email,
                        "name": admin_user.full_name,
                        "response": "accepted",
                    },
                    {
                        "email": "marie.martin@email.be",
                        "name": "Marie Martin",
                        "response": "accepted",
                    },
                ],
                is_all_day=False,
                status="confirmed",
            )
            session.add(event3)
            calendar_count += 1

            # Event 4: Consultation client (future)
            event4 = CalendarEvent(
                id=uuid4(),
                tenant_id=tenant.id,
                user_id=admin_user.id,
                case_id=None,  # Nouveau client potentiel
                external_id=f"google-event-{uuid4()}",
                provider="google",
                title="Première consultation - Sophie Laurent",
                description="Nouveau dossier potentiel: litige avec assurance habitation",
                start_time=datetime.now() + timedelta(days=3, hours=14),
                end_time=datetime.now() + timedelta(days=3, hours=15),
                location="Cabinet - Bureau Maître Simon",
                attendees=[
                    {
                        "email": admin_user.email,
                        "name": admin_user.full_name,
                        "response": "accepted",
                    },
                    {
                        "email": "sophie.laurent@email.be",
                        "name": "Sophie Laurent",
                        "response": "tentative",
                    },
                ],
                is_all_day=False,
                status="tentative",
            )
            session.add(event4)
            calendar_count += 1

            # Event 5: Réunion interne (today)
            event5 = CalendarEvent(
                id=uuid4(),
                tenant_id=tenant.id,
                user_id=admin_user.id,
                case_id=None,
                external_id=f"outlook-event-{uuid4()}",
                provider="outlook",
                title="Réunion équipe - Point hebdomadaire",
                description="Revue des dossiers en cours et planification de la semaine",
                start_time=datetime.now().replace(
                    hour=9, minute=0, second=0, microsecond=0
                ),
                end_time=datetime.now().replace(
                    hour=10, minute=0, second=0, microsecond=0
                ),
                location="Cabinet - Salle de réunion",
                attendees=[
                    {
                        "email": admin_user.email,
                        "name": admin_user.full_name,
                        "response": "accepted",
                    }
                ],
                is_all_day=False,
                status="confirmed",
            )
            session.add(event5)
            calendar_count += 1

            # Event 6: Deadline dépôt (future)
            event6 = CalendarEvent(
                id=uuid4(),
                tenant_id=tenant.id,
                user_id=admin_user.id,
                case_id=cases[0].id,  # Dupont c/ Immobel
                external_id=f"google-event-{uuid4()}",
                provider="google",
                title="DEADLINE - Dépôt conclusions Dupont",
                description="Date limite pour déposer nos conclusions écrites au greffe. Dossier 2026/001.",
                start_time=datetime.now()
                + timedelta(days=12).replace(hour=23, minute=59),
                end_time=datetime.now()
                + timedelta(days=12).replace(hour=23, minute=59),
                location="e-Deposit JBox",
                attendees=[
                    {
                        "email": admin_user.email,
                        "name": admin_user.full_name,
                        "response": "accepted",
                    }
                ],
                is_all_day=True,
                status="confirmed",
                metadata_={"type": "deadline", "priority": "high"},
            )
            session.add(event6)
            calendar_count += 1

            # Event 7: Rendez-vous visio (future)
            event7 = CalendarEvent(
                id=uuid4(),
                tenant_id=tenant.id,
                user_id=admin_user.id,
                case_id=cases[2].id,  # TechStart - Recouvrement
                external_id=f"outlook-event-{uuid4()}",
                provider="outlook",
                title="Visioconférence - Négociation TechStart",
                description="Réunion Teams avec les dirigeants de TechStart SPRL pour discuter de la proposition de paiement échelonné",
                start_time=datetime.now() + timedelta(days=7, hours=15),
                end_time=datetime.now() + timedelta(days=7, hours=16),
                location="Microsoft Teams",
                attendees=[
                    {
                        "email": admin_user.email,
                        "name": admin_user.full_name,
                        "response": "accepted",
                    },
                    {
                        "email": "info@techstart.be",
                        "name": "TechStart SPRL",
                        "response": "accepted",
                    },
                ],
                is_all_day=False,
                status="confirmed",
                metadata_={
                    "meeting_url": "https://teams.microsoft.com/l/meetup-join/...",
                    "platform": "teams",
                },
            )
            session.add(event7)
            calendar_count += 1

            # Event 8: Rendez-vous visio (future)
            event8 = CalendarEvent(
                id=uuid4(),
                tenant_id=tenant.id,
                user_id=admin_user.id,
                case_id=cases[4].id,  # Invest Group - Contrôle fiscal
                external_id=f"google-event-{uuid4()}",
                provider="google",
                title="Zoom - Débriefing contrôle fiscal Invest Group",
                description="Point avec le client suite à la clôture du contrôle fiscal TVA",
                start_time=datetime.now() + timedelta(days=10, hours=11),
                end_time=datetime.now() + timedelta(days=10, hours=12),
                location="Zoom",
                attendees=[
                    {
                        "email": admin_user.email,
                        "name": admin_user.full_name,
                        "response": "accepted",
                    },
                    {
                        "email": "info@investgroup.be",
                        "name": "Invest Group",
                        "response": "tentative",
                    },
                ],
                is_all_day=False,
                status="tentative",
                metadata_={"meeting_url": "https://zoom.us/j/...", "platform": "zoom"},
            )
            session.add(event8)
            calendar_count += 1

            await session.flush()
            print(f"✓ {calendar_count} calendar events created")
        except Exception as e:
            print(f"✗ Error creating calendar events: {e}")

        # ── 13. Call Records ──
        print("\n📞 Creating 3 call records...")
        call_records = []

        try:
            # Call 1: Inbound answered - 10 min avec recording et transcription
            call1 = CallRecord(
                id=uuid4(),
                tenant_id=tenant.id,
                case_id=cases[0].id,  # Dupont c/ Immobel
                contact_id=contacts[0].id,  # Jean Dupont
                external_id=f"ringover-call-{uuid4()}",
                direction="inbound",
                caller_number=contacts[0].phone_e164,
                callee_number="+32471111111",
                duration_seconds=600,  # 10 minutes
                call_type="answered",
                recording_url=f"https://recordings.ringover.com/2026/02/call-{uuid4()}.mp3",
                started_at=datetime.now() - timedelta(days=2, hours=14, minutes=30),
                ended_at=datetime.now() - timedelta(days=2, hours=14, minutes=20),
                metadata_={"quality": "HD", "ringover_id": f"RO-{uuid4()}"},
            )
            call_records.append(call1)
            session.add(call1)

            # Call 2: Outbound answered - 5 min
            call2 = CallRecord(
                id=uuid4(),
                tenant_id=tenant.id,
                case_id=cases[1].id,  # Martin - Divorce
                contact_id=contacts[1].id,  # Marie Martin
                external_id=f"ringover-call-{uuid4()}",
                direction="outbound",
                caller_number="+32471111111",
                callee_number=contacts[1].phone_e164,
                duration_seconds=300,  # 5 minutes
                call_type="answered",
                recording_url=f"https://recordings.ringover.com/2026/02/call-{uuid4()}.mp3",
                started_at=datetime.now() - timedelta(days=1, hours=10, minutes=15),
                ended_at=datetime.now() - timedelta(days=1, hours=10, minutes=10),
                metadata_={"quality": "HD", "ringover_id": f"RO-{uuid4()}"},
            )
            call_records.append(call2)
            session.add(call2)

            # Call 3: Inbound missed - 0 min
            call3 = CallRecord(
                id=uuid4(),
                tenant_id=tenant.id,
                case_id=cases[2].id,  # TechStart - Recouvrement
                contact_id=contacts[6].id,  # SPRL TechStart
                external_id=f"ringover-call-{uuid4()}",
                direction="inbound",
                caller_number="+32471234567",  # Contact TechStart
                callee_number="+32471111111",
                duration_seconds=0,
                call_type="missed",
                recording_url=None,
                started_at=datetime.now() - timedelta(hours=3, minutes=45),
                ended_at=datetime.now() - timedelta(hours=3, minutes=45),
                metadata_={"ringover_id": f"RO-{uuid4()}", "voicemail": False},
            )
            call_records.append(call3)
            session.add(call3)

            await session.flush()
            print(f"✓ {len(call_records)} call records created")
        except Exception as e:
            print(f"✗ Error creating call records: {e}")

        # ── 14. Transcriptions ──
        print("\n🎙️  Creating 2 transcriptions with segments...")
        transcription_count = 0
        segment_count = 0

        try:
            # Transcription 1: Appel Ringover avec client Dupont (lié à call1)
            trans1_full_text = """Avocat: Bonjour Monsieur Dupont, Maître Simon à l'appareil.
Client: Bonjour Maître, merci de me rappeler si rapidement.
Avocat: Je vous en prie. J'ai examiné les nouveaux documents que vous m'avez transmis concernant votre litige avec Immobel.
Client: Oui, justement, j'aimerais savoir où nous en sommes. Les dommages au bâtiment sont vraiment importants.
Avocat: Effectivement, j'ai bien noté les photos et le rapport d'expertise. Nous avons de solides arguments pour réclamer des dommages et intérêts substantiels.
Client: C'est une bonne nouvelle. Quelles sont les prochaines étapes?
Avocat: Je vais rédiger une mise en demeure formelle cette semaine. Ensuite, si Immobel ne répond pas favorablement dans les 15 jours, nous introduisons la procédure au tribunal.
Client: Parfait. Et concernant les frais d'avocat?
Avocat: Nous pourrons les inclure dans notre demande de dommages et intérêts. Je vous enverrai une estimation détaillée par email demain.
Client: Très bien, je vous remercie pour votre réactivité Maître."""

            trans1 = Transcription(
                id=uuid4(),
                tenant_id=tenant.id,
                case_id=cases[0].id,  # Dupont c/ Immobel
                call_record_id=call_records[0].id,
                source="ringover",
                audio_url=call_records[0].recording_url,
                audio_duration_seconds=600,
                language="fr",
                status="completed",
                full_text=trans1_full_text,
                summary="Discussion sur l'avancement du dossier Dupont c/ Immobel. Le client s'inquiète des dommages importants. L'avocat confirme avoir des arguments solides et prévoit d'envoyer une mise en demeure cette semaine, suivie d'une procédure au tribunal si nécessaire. Estimation des frais à transmettre par email.",
                sentiment_score=0.7,
                sentiment_label="positive",
                extracted_tasks=[
                    {
                        "title": "Rédiger mise en demeure Immobel",
                        "description": "Préparer mise en demeure formelle pour dommages et intérêts",
                        "due_date": str(date.today() + timedelta(days=7)),
                        "priority": "high",
                    },
                    {
                        "title": "Envoyer estimation frais à M. Dupont",
                        "description": "Transmettre estimation détaillée des honoraires par email",
                        "due_date": str(date.today() + timedelta(days=1)),
                        "priority": "medium",
                    },
                ],
                completed_at=datetime.now() - timedelta(days=2, hours=14, minutes=20),
            )
            session.add(trans1)
            await session.flush()
            transcription_count += 1

            # Segments pour Transcription 1 (10 segments)
            trans1_segments = [
                (
                    0,
                    "Avocat",
                    0.0,
                    4.2,
                    "Bonjour Monsieur Dupont, Maître Simon à l'appareil.",
                    0.98,
                ),
                (
                    1,
                    "Client",
                    4.2,
                    8.5,
                    "Bonjour Maître, merci de me rappeler si rapidement.",
                    0.96,
                ),
                (
                    2,
                    "Avocat",
                    8.5,
                    18.3,
                    "Je vous en prie. J'ai examiné les nouveaux documents que vous m'avez transmis concernant votre litige avec Immobel.",
                    0.97,
                ),
                (
                    3,
                    "Client",
                    18.3,
                    28.7,
                    "Oui, justement, j'aimerais savoir où nous en sommes. Les dommages au bâtiment sont vraiment importants.",
                    0.95,
                ),
                (
                    4,
                    "Avocat",
                    28.7,
                    42.1,
                    "Effectivement, j'ai bien noté les photos et le rapport d'expertise. Nous avons de solides arguments pour réclamer des dommages et intérêts substantiels.",
                    0.98,
                ),
                (
                    5,
                    "Client",
                    42.1,
                    47.5,
                    "C'est une bonne nouvelle. Quelles sont les prochaines étapes?",
                    0.97,
                ),
                (
                    6,
                    "Avocat",
                    47.5,
                    62.8,
                    "Je vais rédiger une mise en demeure formelle cette semaine. Ensuite, si Immobel ne répond pas favorablement dans les 15 jours, nous introduisons la procédure au tribunal.",
                    0.96,
                ),
                (
                    7,
                    "Client",
                    62.8,
                    68.2,
                    "Parfait. Et concernant les frais d'avocat?",
                    0.98,
                ),
                (
                    8,
                    "Avocat",
                    68.2,
                    80.5,
                    "Nous pourrons les inclure dans notre demande de dommages et intérêts. Je vous enverrai une estimation détaillée par email demain.",
                    0.97,
                ),
                (
                    9,
                    "Client",
                    80.5,
                    87.0,
                    "Très bien, je vous remercie pour votre réactivité Maître.",
                    0.99,
                ),
            ]

            for idx, speaker, start, end, text, confidence in trans1_segments:
                segment = TranscriptionSegment(
                    id=uuid4(),
                    transcription_id=trans1.id,
                    segment_index=idx,
                    speaker=speaker,
                    start_time=start,
                    end_time=end,
                    text=text,
                    confidence=confidence,
                )
                session.add(segment)
                segment_count += 1

            # Transcription 2: Note audio Plaud (dictée avocat)
            trans2_full_text = """Note pour le dossier Martin, divorce par consentement mutuel.
Suite à la réunion de ce matin avec Madame Martin et son époux.
Les deux parties sont d'accord sur les modalités suivantes:
Premièrement, garde alternée des deux enfants, une semaine sur deux, avec changement le vendredi soir.
Deuxièmement, partage équitable des biens immobiliers. La maison familiale à Uccle sera vendue et le produit partagé à parts égales.
Troisièmement, pension alimentaire de 800 euros par mois versée par Monsieur pour les enfants.
Action à prévoir: rédiger la convention de divorce et prendre rendez-vous avec le notaire pour l'acte de partage.
Deadline: signature prévue pour fin mars."""

            trans2 = Transcription(
                id=uuid4(),
                tenant_id=tenant.id,
                case_id=cases[1].id,  # Martin - Divorce
                call_record_id=None,  # Pas lié à un appel
                source="plaud",
                audio_url=f"https://storage.lexibel.be/audio/plaud-{uuid4()}.m4a",
                audio_duration_seconds=95,
                language="fr",
                status="completed",
                full_text=trans2_full_text,
                summary="Note dictée sur le dossier de divorce Martin. Accord trouvé sur: garde alternée une semaine sur deux, vente et partage de la maison d'Uccle, pension alimentaire de 800€/mois. Actions: rédiger convention et rdv notaire pour fin mars.",
                sentiment_score=0.6,
                sentiment_label="neutral",
                extracted_tasks=[
                    {
                        "title": "Rédiger convention divorce Martin",
                        "description": "Préparer la convention de divorce par consentement mutuel avec les modalités convenues",
                        "due_date": str(date.today() + timedelta(days=14)),
                        "priority": "high",
                    },
                    {
                        "title": "Rendez-vous notaire partage Martin",
                        "description": "Organiser RDV avec notaire pour acte de partage maison Uccle",
                        "due_date": str(date.today() + timedelta(days=30)),
                        "priority": "medium",
                    },
                ],
                completed_at=datetime.now() - timedelta(hours=2),
            )
            session.add(trans2)
            await session.flush()
            transcription_count += 1

            # Segments pour Transcription 2 (8 segments)
            trans2_segments = [
                (
                    0,
                    "Avocat",
                    0.0,
                    6.5,
                    "Note pour le dossier Martin, divorce par consentement mutuel.",
                    0.99,
                ),
                (
                    1,
                    "Avocat",
                    6.5,
                    12.8,
                    "Suite à la réunion de ce matin avec Madame Martin et son époux.",
                    0.98,
                ),
                (
                    2,
                    "Avocat",
                    12.8,
                    18.2,
                    "Les deux parties sont d'accord sur les modalités suivantes:",
                    0.97,
                ),
                (
                    3,
                    "Avocat",
                    18.2,
                    30.5,
                    "Premièrement, garde alternée des deux enfants, une semaine sur deux, avec changement le vendredi soir.",
                    0.96,
                ),
                (
                    4,
                    "Avocat",
                    30.5,
                    45.8,
                    "Deuxièmement, partage équitable des biens immobiliers. La maison familiale à Uccle sera vendue et le produit partagé à parts égales.",
                    0.97,
                ),
                (
                    5,
                    "Avocat",
                    45.8,
                    56.3,
                    "Troisièmement, pension alimentaire de 800 euros par mois versée par Monsieur pour les enfants.",
                    0.98,
                ),
                (
                    6,
                    "Avocat",
                    56.3,
                    72.1,
                    "Action à prévoir: rédiger la convention de divorce et prendre rendez-vous avec le notaire pour l'acte de partage.",
                    0.96,
                ),
                (
                    7,
                    "Avocat",
                    72.1,
                    78.5,
                    "Deadline: signature prévue pour fin mars.",
                    0.99,
                ),
            ]

            for idx, speaker, start, end, text, confidence in trans2_segments:
                segment = TranscriptionSegment(
                    id=uuid4(),
                    transcription_id=trans2.id,
                    segment_index=idx,
                    speaker=speaker,
                    start_time=start,
                    end_time=end,
                    text=text,
                    confidence=confidence,
                )
                session.add(segment)
                segment_count += 1

            await session.flush()
            print(
                f"✓ {transcription_count} transcriptions with {segment_count} segments created"
            )
        except Exception as e:
            print(f"✗ Error creating transcriptions: {e}")

        # ── 15. OAuth Tokens ──
        print("\n🔐 Creating 3 OAuth tokens...")
        token_count = 0

        try:
            # Token 1: Google actif (expires dans le futur)
            token1 = OAuthToken(
                id=uuid4(),
                tenant_id=tenant.id,
                user_id=admin_user.id,
                provider="google",
                access_token="ya29.a0AfH6SMBx..." + "x" * 150,  # Encrypted token simulé
                refresh_token="1//0gQ..." + "x" * 100,
                token_type="Bearer",
                expires_at=datetime.now() + timedelta(days=30),
                scope="https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/contacts.readonly",
                is_active=True,
                metadata_={
                    "email": admin_user.email,
                    "last_sync": str(datetime.now() - timedelta(hours=2)),
                    "sync_status": "success",
                },
            )
            session.add(token1)
            token_count += 1

            # Token 2: Microsoft expiré (expires dans le passé)
            token2 = OAuthToken(
                id=uuid4(),
                tenant_id=tenant.id,
                user_id=admin_user.id,
                provider="microsoft",
                access_token="EwBwA8l6BAAUbDba..."
                + "x" * 200,  # Encrypted token simulé
                refresh_token="M.R3_BAY..." + "x" * 150,
                token_type="Bearer",
                expires_at=datetime.now() - timedelta(days=5),  # Expiré
                scope="Mail.Read Calendars.ReadWrite Contacts.Read",
                is_active=False,
                metadata_={
                    "email": admin_user.email,
                    "last_sync": str(datetime.now() - timedelta(days=6)),
                    "sync_status": "expired",
                    "error": "Token expired - needs re-authentication",
                },
            )
            session.add(token2)
            token_count += 1

            # Token 3: Google révoqué (access_token vide, is_active=False)
            token3 = OAuthToken(
                id=uuid4(),
                tenant_id=tenant.id,
                user_id=admin_user.id,
                provider="google",
                access_token="",  # Vide car révoqué
                refresh_token="",  # Vide car révoqué
                token_type="Bearer",
                expires_at=datetime.now() - timedelta(days=10),
                scope="https://www.googleapis.com/auth/gmail.readonly",
                is_active=False,
                revoked_at=datetime.now() - timedelta(days=3),
                metadata_={
                    "email": "old.account@gmail.com",
                    "revocation_reason": "User revoked access",
                    "revoked_by": str(admin_user.id),
                },
            )
            session.add(token3)
            token_count += 1

            await session.flush()
            print(f"✓ {token_count} OAuth tokens created")
        except Exception as e:
            print(f"✗ Error creating OAuth tokens: {e}")

        # ── 16. Extended Demo Data — Belgian Legal Realism ──
        print("\n📂 Creating 5 additional cases (Belgian law)...")
        extra_cases = []
        extra_case_data = [
            (
                "2026/006",
                "Divorce Janssens-Peters",
                "family",
                "in_progress",
                "Tribunal de la famille de Namur",
            ),
            (
                "2026/007",
                "SA BelgaTech — Contentieux fiscal",
                "fiscal",
                "open",
                "Cour d'appel de Bruxelles",
            ),
            (
                "2026/008",
                "Accident A4 — Indemnisation Maes",
                "civil",
                "in_progress",
                "Tribunal de police de Liège",
            ),
            (
                "2025/042",
                "Bail commercial Rue Neuve",
                "commercial",
                "closed",
                "Justice de paix de Bruxelles",
            ),
            (
                "2026/009",
                "ASBL SportPlus — Dissolution",
                "commercial",
                "open",
                None,
            ),
        ]

        for ref, title, matter_type, case_status, jurisdiction in extra_case_data:
            case = Case(
                id=uuid4(),
                tenant_id=tenant.id,
                reference=ref,
                title=title,
                matter_type=matter_type,
                status=case_status,
                jurisdiction=jurisdiction,
                responsible_user_id=admin_user.id,
                opened_at=date.today() - timedelta(days=60),
                closed_at=date.today() - timedelta(days=10)
                if case_status == "closed"
                else None,
                metadata_={"tags": ["demo", "extended"], "priority": "medium"},
            )
            extra_cases.append(case)
            session.add(case)

        await session.flush()
        cases.extend(extra_cases)
        print(f"✅ {len(extra_cases)} additional cases created (total: {len(cases)})")

        # ── 17. Additional contacts ──
        print("\n📇 Creating 5 additional contacts...")
        extra_contacts = []

        extra_natural = [
            ("Anne Janssens", "anne.janssens@email.be", "+32475678901"),
            ("Thomas Peters", "thomas.peters@email.be", "+32476789012"),
            ("François Viseur", "francois.viseur@barreau.be", "+32477890123"),
            ("Karine Lambert", "karine.lambert@notaire.be", "+32478901234"),
            ("Sophie Maes", "sophie.maes@email.be", "+32479012345"),
        ]

        for name, email, phone in extra_natural:
            contact = Contact(
                id=uuid4(),
                tenant_id=tenant.id,
                type="natural",
                full_name=name,
                email=email,
                phone_e164=phone,
                language="fr",
                address={
                    "street": "Avenue de la Toison d'Or 45",
                    "city": "Bruxelles",
                    "zip": "1060",
                    "country": "BE",
                },
            )
            extra_contacts.append(contact)
            session.add(contact)

        await session.flush()
        contacts.extend(extra_contacts)
        print(
            f"✅ {len(extra_contacts)} additional contacts created (total: {len(contacts)})"
        )

        # ── 18. Extra case-contact links ──
        print("\n🔗 Linking extra contacts to extra cases...")
        extra_links = [
            (extra_cases[0], extra_contacts[0], "client"),  # Janssens → Divorce
            (extra_cases[0], extra_contacts[1], "client"),  # Peters → Divorce
            (extra_cases[1], contacts[7], "client"),  # SCS Invest → Fiscal
            (extra_cases[2], extra_contacts[4], "client"),  # Maes → Accident
            (extra_cases[3], contacts[5], "client"),  # Immobel → Bail
            (extra_cases[4], contacts[7], "client"),  # SCS Invest → ASBL
        ]

        for case, contact, role in extra_links:
            case_contact = CaseContact(
                tenant_id=tenant.id,
                case_id=case.id,
                contact_id=contact.id,
                role=role,
            )
            session.add(case_contact)

        await session.flush()
        print(f"✅ {len(extra_links)} additional case-contact links created")

        # ── 19. Additional invoices ──
        print("\n💰 Creating 2 additional invoices...")

        invoice4 = Invoice(
            id=uuid4(),
            tenant_id=tenant.id,
            case_id=extra_cases[0].id,
            client_contact_id=extra_contacts[0].id,
            invoice_number="2026/004",
            issue_date=date.today() - timedelta(days=60),
            due_date=date.today() - timedelta(days=30),
            status="overdue",
            subtotal_cents=200000,
            vat_rate=21.0,
            vat_amount_cents=42000,
            total_cents=242000,
        )
        session.add(invoice4)

        line4 = InvoiceLine(
            id=uuid4(),
            tenant_id=tenant.id,
            invoice_id=invoice4.id,
            description="Honoraires — Divorce Janssens-Peters — Phase préparatoire",
            quantity=8.0,
            unit_price_cents=25000,
            total_cents=200000,
        )
        session.add(line4)

        invoice5 = Invoice(
            id=uuid4(),
            tenant_id=tenant.id,
            case_id=extra_cases[2].id,
            client_contact_id=extra_contacts[4].id,
            invoice_number="2026/005",
            issue_date=date.today() - timedelta(days=3),
            due_date=date.today() + timedelta(days=27),
            status="sent",
            subtotal_cents=75000,
            vat_rate=21.0,
            vat_amount_cents=15750,
            total_cents=90750,
        )
        session.add(invoice5)

        line5 = InvoiceLine(
            id=uuid4(),
            tenant_id=tenant.id,
            invoice_id=invoice5.id,
            description="Honoraires — Accident A4 — Constitution de dossier",
            quantity=3.0,
            unit_price_cents=25000,
            total_cents=75000,
        )
        session.add(line5)

        await session.flush()
        print("✅ 2 additional invoices with lines created (total: 5)")

        # ── 20. Additional inbox items ──
        print("\n📥 Creating 3 additional inbox items...")
        extra_inbox = [
            (
                "DPA_JBOX",
                "DRAFT",
                None,
                None,
                "Communication judiciaire — Tribunal de Namur",
            ),
            ("OUTLOOK", "DRAFT", extra_cases[1].id, 0.88, "Rapport fiscal BelgaTech"),
            (
                "RINGOVER",
                "VALIDATED",
                extra_cases[2].id,
                0.92,
                "Message vocal — Sophie Maes",
            ),
        ]

        for i, (source, item_status, suggested_case, confidence, subject) in enumerate(
            extra_inbox
        ):
            item = InboxItem(
                id=uuid4(),
                tenant_id=tenant.id,
                source=source,
                status=item_status,
                raw_payload={
                    "id": f"external-extended-{source.lower()}-{i + 1}",
                    "from": f"sender_ext{i + 1}@example.com",
                    "subject": subject,
                    "body": f"Contenu étendu #{i + 1}",
                    "received_at": str(datetime.now() - timedelta(hours=i + 1)),
                },
                suggested_case_id=suggested_case,
                confidence=confidence,
                validated_by=admin_user.id if item_status == "VALIDATED" else None,
                validated_at=datetime.now() - timedelta(hours=i)
                if item_status == "VALIDATED"
                else None,
            )
            session.add(item)

        await session.flush()
        print("✅ 3 additional inbox items created (total: 8)")

        # ── Commit All ──
        print("\n💾 Committing all changes...")
        await session.commit()
        print("✅ All data committed!")

        print("\n" + "=" * 60)
        print("🎉 Demo data seed completed successfully!")
        print("=" * 60)
        print("\n📊 Summary:")
        print(f"  • Tenant: {tenant.name}")
        print(f"  • Admin user: {admin_user.email} (password: admin123)")
        print(f"  • Cases: {len(cases)}")
        print(f"  • Contacts: {len(contacts)}")
        print(f"  • Case-Contact links: {len(case_contacts) + len(extra_links)}")
        print("  • Timeline events: 20")
        print(f"  • Time entries: {len(time_entries)}")
        print("  • Invoices: 5")
        print("  • Third-party entries: 2")
        print("  • Inbox items: 8")
        print(f"  • Email threads: {thread_count} (with {message_count} messages)")
        print(f"  • Calendar events: {calendar_count}")
        print(f"  • Call records: {len(call_records)}")
        print(
            f"  • Transcriptions: {transcription_count} (with {segment_count} segments)"
        )
        print(f"  • OAuth tokens: {token_count}")
        print("\n✅ You can now login at https://lexibel.clixite.cloud")
        print(f"   Email: {admin_user.email}")
        print("   Password: admin123")
        print()


if __name__ == "__main__":
    asyncio.run(seed_data())
