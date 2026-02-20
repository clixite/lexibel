"""Invoice service — creation, valorisation, Peppol UBL generation."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.invoice import Invoice
from packages.db.models.invoice_line import InvoiceLine
from packages.db.models.time_entry import TimeEntry


async def create_invoice(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    invoice_number: str,
    client_contact_id: uuid.UUID,
    due_date: date,
    case_id: uuid.UUID | None = None,
    issue_date: date | None = None,
    vat_rate: Decimal = Decimal("21.00"),
    currency: str = "EUR",
    notes: str | None = None,
    lines: list[dict] | None = None,
    time_entry_ids: list[uuid.UUID] | None = None,
) -> Invoice:
    """Create an invoice, optionally auto-valorising from time entries."""
    invoice = Invoice(
        tenant_id=tenant_id,
        case_id=case_id,
        invoice_number=invoice_number,
        client_contact_id=client_contact_id,
        issue_date=issue_date or date.today(),
        due_date=due_date,
        vat_rate=vat_rate,
        currency=currency,
        notes=notes,
    )
    session.add(invoice)
    await session.flush()
    await session.refresh(invoice)

    all_lines: list[InvoiceLine] = []

    # Auto-valorise from time entries
    if time_entry_ids:
        result = await session.execute(
            select(TimeEntry).where(
                TimeEntry.id.in_(time_entry_ids),
                TimeEntry.status == "approved",
            )
        )
        entries = list(result.scalars().all())
        for idx, entry in enumerate(entries):
            rate = entry.hourly_rate_cents or 0
            hours = Decimal(str(entry.duration_minutes)) / Decimal("60")
            line_total = int(hours * rate)
            line = InvoiceLine(
                tenant_id=tenant_id,
                invoice_id=invoice.id,
                description=entry.description,
                quantity=hours,
                unit_price_cents=rate,
                total_cents=line_total,
                time_entry_id=entry.id,
                sort_order=idx,
            )
            session.add(line)
            all_lines.append(line)

            # Mark time entry as invoiced
            entry.status = "invoiced"

    # Manual lines
    if lines:
        offset = len(all_lines)
        for idx, line_data in enumerate(lines):
            quantity = Decimal(str(line_data["quantity"]))
            unit_price = line_data["unit_price_cents"]
            line_total = int(quantity * unit_price)
            line = InvoiceLine(
                tenant_id=tenant_id,
                invoice_id=invoice.id,
                description=line_data["description"],
                quantity=quantity,
                unit_price_cents=unit_price,
                total_cents=line_total,
                time_entry_id=line_data.get("time_entry_id"),
                sort_order=line_data.get("sort_order", offset + idx),
            )
            session.add(line)
            all_lines.append(line)

    # Calculate totals
    subtotal = sum(line.total_cents for line in all_lines)
    vat_amount = int(subtotal * vat_rate / Decimal("100"))
    total = subtotal + vat_amount

    invoice.subtotal_cents = subtotal
    invoice.vat_amount_cents = vat_amount
    invoice.total_cents = total

    await session.flush()
    await session.refresh(invoice)
    return invoice


async def get_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
) -> Invoice | None:
    """Get a single invoice by ID (RLS filters by tenant)."""
    result = await session.execute(select(Invoice).where(Invoice.id == invoice_id))
    return result.scalar_one_or_none()


async def get_invoice_lines(
    session: AsyncSession,
    invoice_id: uuid.UUID,
) -> list[InvoiceLine]:
    """Get all lines for an invoice."""
    result = await session.execute(
        select(InvoiceLine)
        .where(InvoiceLine.invoice_id == invoice_id)
        .order_by(InvoiceLine.sort_order.asc())
    )
    return list(result.scalars().all())


async def list_invoices(
    session: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
    case_id: Optional[uuid.UUID] = None,
) -> tuple[list[Invoice], int]:
    """List invoices with pagination and filters."""
    query = select(Invoice)

    if status:
        query = query.where(Invoice.status == status)
    if case_id:
        query = query.where(Invoice.case_id == case_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    query = query.order_by(Invoice.issue_date.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    items = list(result.scalars().all())
    return items, total


async def update_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
    **kwargs,
) -> Invoice | None:
    """Update a draft invoice. Only draft invoices can be modified."""
    invoice = await get_invoice(session, invoice_id)
    if invoice is None:
        return None

    if invoice.status != "draft":
        return invoice  # Only draft invoices can be updated

    for key, value in kwargs.items():
        if value is not None and hasattr(invoice, key):
            setattr(invoice, key, value)

    await session.flush()
    await session.refresh(invoice)
    return invoice


async def cancel_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
) -> Invoice | None:
    """Cancel an invoice (soft delete). Sets status to 'cancelled'."""
    invoice = await get_invoice(session, invoice_id)
    if invoice is None:
        return None

    invoice.status = "cancelled"
    await session.flush()
    await session.refresh(invoice)
    return invoice


def generate_peppol_ubl(
    invoice: Invoice,
    lines: list[InvoiceLine],
    supplier_name: str = "Cabinet d'avocats",
    supplier_vat: str = "BE0000000000",
) -> str:
    """Generate UBL 2.1 / BIS Billing 3.0 XML for Peppol e-invoicing.

    Returns well-formed XML string conforming to PEPPOL BIS Billing 3.0.
    """
    ns = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
    cac = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    cbc = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

    root = Element("Invoice", xmlns=ns)
    root.set("xmlns:cac", cac)
    root.set("xmlns:cbc", cbc)

    # Header
    _sub(
        root,
        f"{{{cbc}}}CustomizationID",
        "urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0",
    )
    _sub(root, f"{{{cbc}}}ProfileID", "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0")
    _sub(root, f"{{{cbc}}}ID", invoice.invoice_number)
    _sub(root, f"{{{cbc}}}IssueDate", str(invoice.issue_date))
    _sub(root, f"{{{cbc}}}DueDate", str(invoice.due_date))
    _sub(root, f"{{{cbc}}}InvoiceTypeCode", "380")
    _sub(root, f"{{{cbc}}}DocumentCurrencyCode", invoice.currency)

    # Supplier
    supplier_party = SubElement(root, f"{{{cac}}}AccountingSupplierParty")
    party = SubElement(supplier_party, f"{{{cac}}}Party")
    party_name = SubElement(party, f"{{{cac}}}PartyName")
    _sub(party_name, f"{{{cbc}}}Name", supplier_name)
    tax_scheme_el = SubElement(party, f"{{{cac}}}PartyTaxScheme")
    _sub(tax_scheme_el, f"{{{cbc}}}CompanyID", supplier_vat)
    scheme = SubElement(tax_scheme_el, f"{{{cac}}}TaxScheme")
    _sub(scheme, f"{{{cbc}}}ID", "VAT")

    # Customer (placeholder — filled from contact in production)
    customer_party = SubElement(root, f"{{{cac}}}AccountingCustomerParty")
    cust_party = SubElement(customer_party, f"{{{cac}}}Party")
    cust_name = SubElement(cust_party, f"{{{cac}}}PartyName")
    _sub(cust_name, f"{{{cbc}}}Name", str(invoice.client_contact_id))

    # Tax total
    tax_total = SubElement(root, f"{{{cac}}}TaxTotal")
    _sub(
        tax_total,
        f"{{{cbc}}}TaxAmount",
        _cents_to_eur(invoice.vat_amount_cents),
        currencyID=invoice.currency,
    )

    # Legal monetary total
    monetary = SubElement(root, f"{{{cac}}}LegalMonetaryTotal")
    _sub(
        monetary,
        f"{{{cbc}}}LineExtensionAmount",
        _cents_to_eur(invoice.subtotal_cents),
        currencyID=invoice.currency,
    )
    _sub(
        monetary,
        f"{{{cbc}}}TaxExclusiveAmount",
        _cents_to_eur(invoice.subtotal_cents),
        currencyID=invoice.currency,
    )
    _sub(
        monetary,
        f"{{{cbc}}}TaxInclusiveAmount",
        _cents_to_eur(invoice.total_cents),
        currencyID=invoice.currency,
    )
    _sub(
        monetary,
        f"{{{cbc}}}PayableAmount",
        _cents_to_eur(invoice.total_cents),
        currencyID=invoice.currency,
    )

    # Invoice lines
    for idx, line in enumerate(lines, 1):
        inv_line = SubElement(root, f"{{{cac}}}InvoiceLine")
        _sub(inv_line, f"{{{cbc}}}ID", str(idx))
        _sub(inv_line, f"{{{cbc}}}InvoicedQuantity", str(line.quantity), unitCode="HUR")
        _sub(
            inv_line,
            f"{{{cbc}}}LineExtensionAmount",
            _cents_to_eur(line.total_cents),
            currencyID=invoice.currency,
        )
        item = SubElement(inv_line, f"{{{cac}}}Item")
        _sub(item, f"{{{cbc}}}Name", line.description[:100])
        price = SubElement(inv_line, f"{{{cac}}}Price")
        _sub(
            price,
            f"{{{cbc}}}PriceAmount",
            _cents_to_eur(line.unit_price_cents),
            currencyID=invoice.currency,
        )

    return tostring(root, encoding="unicode", xml_declaration=True)


def _sub(parent: Element, tag: str, text: str, **attribs) -> Element:
    """Helper to create a subelement with text and attributes."""
    el = SubElement(parent, tag, **attribs)
    el.text = text
    return el


def _cents_to_eur(cents: int) -> str:
    """Convert cents to EUR string with 2 decimal places."""
    return f"{cents / 100:.2f}"


async def generate_peppol_for_invoice(
    session: AsyncSession,
    invoice_id: uuid.UUID,
) -> Invoice | None:
    """Generate Peppol UBL XML for an invoice and store it."""
    invoice = await get_invoice(session, invoice_id)
    if invoice is None:
        return None

    lines = await get_invoice_lines(session, invoice_id)
    xml = generate_peppol_ubl(invoice, lines)

    invoice.peppol_ubl_xml = xml
    invoice.peppol_status = "generated"

    await session.flush()
    await session.refresh(invoice)
    return invoice


async def send_peppol(
    session: AsyncSession,
    invoice_id: uuid.UUID,
) -> Invoice | None:
    """Stub: Send invoice via Peppol network.

    In production, this would connect to a Peppol Access Point.
    """
    invoice = await get_invoice(session, invoice_id)
    if invoice is None:
        return None

    if invoice.peppol_status not in ("generated",):
        return invoice

    # TODO: Send to Peppol Access Point
    invoice.peppol_status = "sent"
    await session.flush()
    await session.refresh(invoice)
    return invoice


async def mark_paid(
    session: AsyncSession,
    invoice_id: uuid.UUID,
) -> Invoice | None:
    """Mark an invoice as paid."""
    invoice = await get_invoice(session, invoice_id)
    if invoice is None:
        return None

    invoice.status = "paid"
    await session.flush()
    await session.refresh(invoice)
    return invoice
