"""DocumentAssembler — generate legal documents from templates + case data.

Templates: mise_en_demeure, conclusions, requete_unilaterale, citation.
Merge case contacts, facts, legal references. Variable replacement with Jinja2.
Output as text (DOCX generation via python-docx in production).
"""
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class AssembledDocument:
    """Result of document assembly."""
    template_name: str
    content: str  # Assembled text content
    format: str = "text"  # text, docx, pdf
    metadata: dict = field(default_factory=dict)
    variables_used: list[str] = field(default_factory=list)
    missing_variables: list[str] = field(default_factory=list)


# ── Template definitions ──

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "infra", "templates")

AVAILABLE_TEMPLATES = {
    "mise_en_demeure": {
        "name": "Mise en demeure",
        "description": "Lettre de mise en demeure formelle",
        "category": "correspondence",
        "required_variables": ["sender_name", "sender_address", "recipient_name", "recipient_address", "facts", "demand", "deadline_days"],
        "optional_variables": ["case_reference", "legal_basis", "city"],
    },
    "conclusions": {
        "name": "Conclusions",
        "description": "Conclusions judiciaires (premières conclusions ou conclusions additionnelles)",
        "category": "judicial",
        "required_variables": ["court_name", "case_number", "plaintiff_name", "defendant_name", "facts", "legal_arguments", "demands"],
        "optional_variables": ["case_reference", "lawyer_name", "lawyer_bar"],
    },
    "requete_unilaterale": {
        "name": "Requête unilatérale",
        "description": "Requête unilatérale adressée au juge",
        "category": "judicial",
        "required_variables": ["court_name", "requester_name", "requester_address", "object", "facts", "legal_basis", "demand"],
        "optional_variables": ["case_reference", "urgency_reason"],
    },
    "citation": {
        "name": "Citation à comparaître",
        "description": "Citation à comparaître devant le tribunal",
        "category": "judicial",
        "required_variables": ["court_name", "plaintiff_name", "defendant_name", "defendant_address", "hearing_date", "object", "facts", "demands"],
        "optional_variables": ["case_reference", "bailiff_name"],
    },
}

# ── Built-in templates (Jinja2-style) ──

_BUILTIN_TEMPLATES = {
    "mise_en_demeure": """MISE EN DEMEURE

{{ city|default("Bruxelles") }}, le {{ date }}

{{ sender_name }}
{{ sender_address }}

À l'attention de :
{{ recipient_name }}
{{ recipient_address }}

{% if case_reference %}Référence : {{ case_reference }}{% endif %}

Madame, Monsieur,

Par la présente, je me permets de vous mettre en demeure de satisfaire aux obligations ci-après décrites.

FAITS :
{{ facts }}

MISE EN DEMEURE :
{{ demand }}

{% if legal_basis %}BASE LÉGALE :
{{ legal_basis }}{% endif %}

En conséquence, je vous mets formellement en demeure de donner suite à la présente dans un délai de {{ deadline_days }} jours à compter de la réception de la présente.

À défaut de réponse satisfaisante dans le délai imparti, je me verrai contraint(e) de saisir les juridictions compétentes afin de faire valoir mes droits, sans autre avis ni mise en demeure.

Veuillez agréer, Madame, Monsieur, l'expression de mes salutations distinguées.

{{ sender_name }}""",

    "conclusions": """CONCLUSIONS

Devant le {{ court_name }}

AFFAIRE : {{ case_number }}
{{ plaintiff_name }} c/ {{ defendant_name }}

{% if case_reference %}Référence interne : {{ case_reference }}{% endif %}

I. FAITS

{{ facts }}

II. DISCUSSION — MOYENS DE DROIT

{{ legal_arguments }}

III. DISPOSITIF

PAR CES MOTIFS,

Plaise au Tribunal de :

{{ demands }}

{% if lawyer_name %}
{{ lawyer_name }}
{% if lawyer_bar %}Avocat au Barreau de {{ lawyer_bar }}{% endif %}
{% endif %}""",

    "requete_unilaterale": """REQUÊTE UNILATÉRALE

À Monsieur/Madame le Président du {{ court_name }}

REQUÉRANT :
{{ requester_name }}
{{ requester_address }}

{% if case_reference %}Référence : {{ case_reference }}{% endif %}

OBJET :
{{ object }}

{% if urgency_reason %}
URGENCE :
{{ urgency_reason }}
{% endif %}

FAITS :
{{ facts }}

BASE LÉGALE :
{{ legal_basis }}

PAR CES MOTIFS,

Le requérant demande respectueusement à Monsieur/Madame le Président de bien vouloir :

{{ demand }}""",

    "citation": """CITATION À COMPARAÎTRE

L'AN DEUX MILLE VINGT-SIX, le {{ date }}

À la requête de :
{{ plaintiff_name }}

{% if bailiff_name %}Par le ministère de {{ bailiff_name }}, Huissier de Justice{% endif %}

J'AI CITÉ :
{{ defendant_name }}
demeurant à {{ defendant_address }}

À COMPARAÎTRE le {{ hearing_date }}
devant le {{ court_name }}

{% if case_reference %}Référence : {{ case_reference }}{% endif %}

OBJET :
{{ object }}

FAITS :
{{ facts }}

DEMANDES :
{{ demands }}

Sous toutes réserves et sans reconnaissance préjudiciable.

DONT ACTE.""",
}


class DocumentAssembler:
    """Generate legal documents from templates and case data."""

    def __init__(self) -> None:
        self._templates = dict(_BUILTIN_TEMPLATES)

    def assemble(
        self,
        template_name: str,
        case_data: dict,
        variables: dict,
    ) -> AssembledDocument:
        """Assemble a document from a template.

        Args:
            template_name: Template key (mise_en_demeure, conclusions, etc.)
            case_data: Case data dict (contacts, facts, references)
            variables: Template variable overrides

        Returns:
            AssembledDocument with rendered content
        """
        if template_name not in self._templates:
            raise ValueError(f"Unknown template: {template_name}. Available: {list(self._templates.keys())}")

        template_text = self._templates[template_name]
        template_info = AVAILABLE_TEMPLATES.get(template_name, {})

        # Merge case_data and variables
        context = {
            "date": datetime.now(timezone.utc).strftime("%d/%m/%Y"),
            **case_data,
            **variables,
        }

        # Check required variables
        required = template_info.get("required_variables", [])
        missing = [v for v in required if v not in context or not context[v]]

        # Render template (simple Jinja2-like replacement)
        content = self._render(template_text, context)

        variables_used = [k for k in context if k in template_text]

        return AssembledDocument(
            template_name=template_name,
            content=content,
            format="text",
            metadata={
                "template": template_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "category": template_info.get("category", ""),
            },
            variables_used=variables_used,
            missing_variables=missing,
        )

    def _render(self, template: str, context: dict) -> str:
        """Render a Jinja2-style template with simple variable substitution."""
        result = template

        # Handle {% if var %}...{% endif %} blocks
        def replace_if_block(match):
            var_name = match.group(1).strip()
            content = match.group(2)
            value = context.get(var_name)
            if value:
                # Recursively render content inside the block
                return self._render(content, context)
            return ""

        result = re.sub(
            r"\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}",
            replace_if_block,
            result,
            flags=re.DOTALL,
        )

        # Handle {{ var|default("value") }}
        def replace_with_default(match):
            var_name = match.group(1).strip()
            default_val = match.group(2).strip().strip('"').strip("'")
            return str(context.get(var_name, default_val))

        result = re.sub(
            r"\{\{\s*(\w+)\|default\([\"']([^\"']*)[\"']\)\s*\}\}",
            replace_with_default,
            result,
        )

        # Handle {{ var }}
        def replace_var(match):
            var_name = match.group(1).strip()
            value = context.get(var_name, "")
            return str(value) if value else f"[{var_name}]"

        result = re.sub(r"\{\{\s*(\w+)\s*\}\}", replace_var, result)

        return result

    def list_templates(self) -> list[dict]:
        """List all available templates."""
        return [
            {
                "id": key,
                "name": info.get("name", key),
                "description": info.get("description", ""),
                "category": info.get("category", ""),
                "required_variables": info.get("required_variables", []),
                "optional_variables": info.get("optional_variables", []),
            }
            for key, info in AVAILABLE_TEMPLATES.items()
        ]

    def get_template_info(self, template_name: str) -> Optional[dict]:
        """Get template details."""
        info = AVAILABLE_TEMPLATES.get(template_name)
        if not info:
            return None
        return {
            "id": template_name,
            **info,
        }
