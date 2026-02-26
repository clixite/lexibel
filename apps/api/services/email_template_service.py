"""Email template service — CRUD + variable rendering + Belgian legal defaults.

Provides reusable templates for common Belgian legal correspondence:
- Mise en demeure (formal notice)
- Convocation audience (hearing summons)
- Envoi de conclusions (filing briefs)
- Accusé de réception (acknowledgment)
- Demande de pièces (document request)
- Courrier partie adverse (opposing counsel)
- Relance facture (payment reminder)
"""

import re
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.email_template import EmailTemplate


# ── Built-in Belgian legal templates ──

SYSTEM_TEMPLATES: list[dict] = [
    {
        "name": "Mise en demeure",
        "category": "mise_en_demeure",
        "language": "fr",
        "subject_template": "Mise en demeure — Dossier {case.reference}",
        "body_template": """<p>Cher/Chère {contact.full_name},</p>

<p>Agissant au nom et pour le compte de notre client, {client.full_name},
nous avons l'honneur de vous mettre formellement en demeure de satisfaire
aux obligations suivantes dans un délai de <strong>15 jours</strong> à
compter de la réception de la présente :</p>

<p><em>[Préciser les obligations]</em></p>

<p>À défaut de régularisation dans le délai imparti, nous nous verrons
contraints d'engager toute procédure judiciaire utile à la sauvegarde
des droits de notre client, sans autre avis ni mise en demeure.</p>

<p>La présente vaut mise en demeure au sens des articles 1153 et suivants
de l'ancien Code civil.</p>

<p>Veuillez agréer l'expression de nos salutations distinguées.</p>

<p>{user.full_name}<br/>Avocat au Barreau</p>""",
        "matter_types": [],
    },
    {
        "name": "Convocation audience",
        "category": "convocation",
        "language": "fr",
        "subject_template": "Audience du {hearing_date} — {case.reference} — {case.title}",
        "body_template": """<p>Cher/Chère {contact.full_name},</p>

<p>Nous vous informons que l'affaire <strong>{case.reference}</strong>
est fixée à l'audience du <strong>{hearing_date}</strong> devant
{case.jurisdiction}.</p>

<p><strong>Détails :</strong></p>
<ul>
    <li>Dossier : {case.reference} — {case.title}</li>
    <li>Juridiction : {case.jurisdiction}</li>
    <li>Date : {hearing_date}</li>
    <li>Heure : {hearing_time}</li>
</ul>

<p>Votre présence n'est en principe pas requise. Nous vous tiendrons
informé(e) de l'issue de l'audience dans les meilleurs délais.</p>

<p>N'hésitez pas à nous contacter pour toute question.</p>

<p>Bien à vous,<br/>{user.full_name}</p>""",
        "matter_types": [],
    },
    {
        "name": "Envoi de conclusions",
        "category": "conclusions",
        "language": "fr",
        "subject_template": "Conclusions — {case.reference} — {case.title}",
        "body_template": """<p>Cher/Chère Confrère,</p>

<p>Conformément au calendrier de mise en état, nous avons l'honneur de
vous communiquer ci-joint nos conclusions dans l'affaire
<strong>{case.reference}</strong>.</p>

<p>Nous restons à votre disposition pour tout échange utile à la bonne
administration de la justice.</p>

<p>Confraternellement,<br/>{user.full_name}<br/>Avocat au Barreau</p>""",
        "matter_types": ["civil", "commercial", "family", "social"],
    },
    {
        "name": "Accusé de réception",
        "category": "accusé_reception",
        "language": "fr",
        "subject_template": "Accusé de réception — {case.reference}",
        "body_template": """<p>Cher/Chère {contact.full_name},</p>

<p>Nous accusons bonne réception de votre courrier/email du {received_date}
relatif au dossier <strong>{case.reference}</strong>.</p>

<p>Nous ne manquerons pas de revenir vers vous dans les meilleurs délais
après examen de votre communication.</p>

<p>Bien à vous,<br/>{user.full_name}</p>""",
        "matter_types": [],
    },
    {
        "name": "Demande de pièces",
        "category": "demande_pieces",
        "language": "fr",
        "subject_template": "Demande de pièces — {case.reference}",
        "body_template": """<p>Cher/Chère {contact.full_name},</p>

<p>Dans le cadre du dossier <strong>{case.reference} — {case.title}</strong>,
nous vous serions reconnaissants de bien vouloir nous transmettre les
documents suivants :</p>

<ol>
    <li><em>[Document 1]</em></li>
    <li><em>[Document 2]</em></li>
    <li><em>[Document 3]</em></li>
</ol>

<p>Nous vous remercions de nous faire parvenir ces pièces dans un délai
de <strong>15 jours</strong>. Ces documents sont nécessaires à la bonne
conduite de votre dossier.</p>

<p>Bien à vous,<br/>{user.full_name}</p>""",
        "matter_types": [],
    },
    {
        "name": "Courrier partie adverse",
        "category": "courrier_adverse",
        "language": "fr",
        "subject_template": "Dossier {case.reference} — {case.title}",
        "body_template": """<p>Cher/Chère Confrère,</p>

<p>En référence au dossier <strong>{case.reference}</strong> opposant
nos clients respectifs, nous souhaitons attirer votre attention sur
les éléments suivants :</p>

<p><em>[Corps du courrier]</em></p>

<p>Nous restons dans l'attente de votre retour et vous prions d'agréer,
cher/chère Confrère, l'expression de nos sentiments confraternels.</p>

<p>{user.full_name}<br/>Avocat au Barreau</p>""",
        "matter_types": [],
    },
    {
        "name": "Relance facture impayée",
        "category": "relance",
        "language": "fr",
        "subject_template": "Rappel — Facture {invoice_number} impayée",
        "body_template": """<p>Cher/Chère {contact.full_name},</p>

<p>Sauf erreur de notre part, nous constatons que notre facture
n° <strong>{invoice_number}</strong> du {invoice_date} d'un montant de
<strong>{invoice_amount} EUR</strong> reste impayée à ce jour.</p>

<p>Nous vous serions reconnaissants de bien vouloir procéder au règlement
dans les meilleurs délais sur le compte suivant :</p>

<p><strong>IBAN : {firm_iban}</strong></p>

<p>Si le paiement a été effectué entre-temps, nous vous prions de ne pas
tenir compte du présent rappel.</p>

<p>Bien à vous,<br/>{user.full_name}</p>""",
        "matter_types": [],
    },
]


def render_template(
    template_str: str,
    variables: dict,
) -> str:
    """Render a template string with variable substitution.

    Supports {variable.field} syntax. Missing variables are left as-is.
    """

    def _replace(match: re.Match) -> str:
        key = match.group(1)
        parts = key.split(".")
        value = variables
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, match.group(0))
            else:
                return match.group(0)
        return str(value) if not isinstance(value, dict) else match.group(0)

    return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_.]*)\}", _replace, template_str)


async def seed_system_templates(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> int:
    """Seed built-in system templates for a tenant. Idempotent."""
    created = 0
    for tpl in SYSTEM_TEMPLATES:
        existing = await session.execute(
            select(EmailTemplate).where(
                EmailTemplate.tenant_id == tenant_id,
                EmailTemplate.name == tpl["name"],
                EmailTemplate.is_system.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            continue

        template = EmailTemplate(
            tenant_id=tenant_id,
            name=tpl["name"],
            category=tpl["category"],
            language=tpl["language"],
            subject_template=tpl["subject_template"],
            body_template=tpl["body_template"],
            matter_types=tpl["matter_types"],
            is_system=True,
        )
        session.add(template)
        created += 1

    if created:
        await session.flush()
    return created


async def list_templates(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    category: str | None = None,
    language: str | None = None,
    matter_type: str | None = None,
) -> list[EmailTemplate]:
    """List email templates with optional filters (defense-in-depth tenant filter)."""
    query = (
        select(EmailTemplate)
        .where(
            EmailTemplate.tenant_id == tenant_id,
        )
        .order_by(EmailTemplate.name)
    )

    if category:
        query = query.where(EmailTemplate.category == category)
    if language:
        query = query.where(EmailTemplate.language == language)
    if matter_type:
        # Filter templates applicable to this matter type (or all)
        query = query.where(
            EmailTemplate.matter_types.op("@>")(f'["{matter_type}"]')
            | (EmailTemplate.matter_types == [])
        )

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_template(
    session: AsyncSession,
    template_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> EmailTemplate | None:
    """Get a single template by ID (defense-in-depth tenant filter)."""
    query = select(EmailTemplate).where(EmailTemplate.id == template_id)
    if tenant_id is not None:
        query = query.where(EmailTemplate.tenant_id == tenant_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def create_template(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    **kwargs,
) -> EmailTemplate:
    """Create a custom email template."""
    template = EmailTemplate(tenant_id=tenant_id, **kwargs)
    session.add(template)
    await session.flush()
    await session.refresh(template)
    return template


async def update_template(
    session: AsyncSession,
    template_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
    **kwargs,
) -> EmailTemplate | None:
    """Update a template. System templates cannot be modified."""
    template = await get_template(session, template_id, tenant_id=tenant_id)
    if template is None:
        return None
    if template.is_system:
        raise ValueError("System templates cannot be modified")

    for key, value in kwargs.items():
        if value is not None:
            setattr(template, key, value)

    await session.flush()
    await session.refresh(template)
    return template


async def delete_template(
    session: AsyncSession,
    template_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> bool:
    """Delete a template. System templates cannot be deleted."""
    template = await get_template(session, template_id, tenant_id=tenant_id)
    if template is None:
        return False
    if template.is_system:
        raise ValueError("System templates cannot be deleted")

    await session.delete(template)
    await session.flush()
    return True


async def render_for_case(
    session: AsyncSession,
    template_id: uuid.UUID,
    case_id: uuid.UUID,
    contact_id: uuid.UUID | None = None,
    extra_vars: dict | None = None,
    tenant_id: uuid.UUID | None = None,
) -> dict:
    """Render a template with case/contact data populated.

    Returns:
        {"subject": "rendered subject", "body": "rendered HTML body"}
    """
    from packages.db.models.case import Case
    from packages.db.models.contact import Contact
    from packages.db.models.user import User

    template = await get_template(session, template_id, tenant_id=tenant_id)
    if not template:
        raise ValueError("Template not found")

    # Load case
    case_result = await session.execute(select(Case).where(Case.id == case_id))
    case = case_result.scalar_one_or_none()
    if not case:
        raise ValueError("Case not found")

    # Load responsible user
    user_result = await session.execute(
        select(User).where(User.id == case.responsible_user_id)
    )
    user = user_result.scalar_one_or_none()

    variables: dict = {
        "case": {
            "reference": case.reference,
            "title": case.title,
            "matter_type": case.matter_type,
            "jurisdiction": case.jurisdiction or "",
            "court_reference": case.court_reference or "",
            "status": case.status,
        },
        "user": {
            "full_name": user.full_name if user else "",
        },
        "today": date.today().strftime("%d/%m/%Y"),
    }

    # Load contact if provided
    if contact_id:
        contact_result = await session.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        contact = contact_result.scalar_one_or_none()
        if contact:
            variables["contact"] = {
                "full_name": contact.full_name,
                "email": contact.email or "",
                "phone": contact.phone_e164 or "",
                "language": contact.language,
            }

    # Merge extra variables
    if extra_vars:
        variables.update(extra_vars)

    return {
        "subject": render_template(template.subject_template, variables),
        "body": render_template(template.body_template, variables),
        "template_id": str(template.id),
        "template_name": template.name,
    }
