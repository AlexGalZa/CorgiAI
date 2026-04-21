"""
Policy Declaration Page Generator (V3 #61)

Generates a PDF declaration page for a given policy using ReportLab.
The declaration page summarises all key policy information for the insured.
"""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from common.constants import COVERAGE_DISPLAY_NAMES
from common.utils import format_address, format_currency

# Corgi brand colours
CORGI_ORANGE = colors.HexColor("#FF5C00")
CORGI_DARK = colors.HexColor("#1D1D1D")
CORGI_GREY = colors.HexColor("#4E4E4E")
CORGI_LIGHT_GREY = colors.HexColor("#F5F6F7")
CORGI_BORDER = colors.HexColor("#D8DEE4")


def _styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle(
        "title",
        parent=base["Normal"],
        fontSize=20,
        fontName="Helvetica-Bold",
        textColor=CORGI_DARK,
        spaceAfter=4,
    )
    styles["subtitle"] = ParagraphStyle(
        "subtitle",
        parent=base["Normal"],
        fontSize=11,
        fontName="Helvetica",
        textColor=CORGI_GREY,
        spaceAfter=2,
    )
    styles["section_header"] = ParagraphStyle(
        "section_header",
        parent=base["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        backColor=CORGI_DARK,
        leftIndent=6,
        spaceBefore=10,
        spaceAfter=0,
        leading=18,
    )
    styles["label"] = ParagraphStyle(
        "label",
        parent=base["Normal"],
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=CORGI_GREY,
        spaceAfter=1,
    )
    styles["value"] = ParagraphStyle(
        "value",
        parent=base["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=CORGI_DARK,
        spaceAfter=4,
    )
    styles["footer"] = ParagraphStyle(
        "footer",
        parent=base["Normal"],
        fontSize=7,
        fontName="Helvetica",
        textColor=CORGI_GREY,
        alignment=TA_CENTER,
    )
    styles["table_header"] = ParagraphStyle(
        "table_header",
        parent=base["Normal"],
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=CORGI_GREY,
    )
    styles["table_cell"] = ParagraphStyle(
        "table_cell",
        parent=base["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=CORGI_DARK,
    )
    styles["amount"] = ParagraphStyle(
        "amount",
        parent=base["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=CORGI_DARK,
        alignment=TA_RIGHT,
    )
    return styles


def _kv_table(pairs: list[tuple[str, str]], styles) -> Table:
    """Two-column key/value table."""
    data = [
        [Paragraph(k, styles["label"]), Paragraph(v, styles["value"])] for k, v in pairs
    ]
    t = Table(data, colWidths=[2 * inch, 4.5 * inch])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ]
        )
    )
    return t


def generate_declaration_page(policy) -> bytes:  # noqa: ANN001
    """Generate a PDF declaration page for the given Policy instance.

    Args:
        policy: A ``policies.models.Policy`` instance.

    Returns:
        PDF bytes of the declaration page.
    """

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    s = _styles()
    story = []

    # ── Header ─────────────────────────────────────────────────────────
    header_data = [
        [
            Paragraph("CORGI INSURANCE", s["title"]),
            Paragraph("POLICY DECLARATIONS PAGE", s["title"]),
        ]
    ]
    header_t = Table(header_data, colWidths=[3.5 * inch, 3 * inch])
    header_t.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(header_t)
    story.append(
        HRFlowable(width="100%", thickness=2, color=CORGI_ORANGE, spaceAfter=8)
    )

    # ── Policy Overview ────────────────────────────────────────────────
    story.append(Paragraph("POLICY INFORMATION", s["section_header"]))
    story.append(Spacer(1, 4))

    quote = policy.quote
    company = quote.company
    address = company.business_address if company else None
    coverage_display = COVERAGE_DISPLAY_NAMES.get(
        policy.coverage_type, policy.coverage_type
    )

    overview_pairs = [
        ("Policy Number:", policy.policy_number),
        ("Coverage Type:", coverage_display),
        ("Carrier:", policy.carrier),
        (
            "Policy Status:",
            policy.get_status_display()
            if hasattr(policy, "get_status_display")
            else policy.status.title(),
        ),
        (
            "Effective Date:",
            policy.effective_date.strftime("%B %d, %Y")
            if policy.effective_date
            else "—",
        ),
        (
            "Expiration Date:",
            policy.expiration_date.strftime("%B %d, %Y")
            if policy.expiration_date
            else "—",
        ),
        (
            "Billing Frequency:",
            policy.billing_frequency.title() if policy.billing_frequency else "Annual",
        ),
    ]
    story.append(_kv_table(overview_pairs, s))

    # ── Insured Information ────────────────────────────────────────────
    story.append(Spacer(1, 6))
    story.append(Paragraph("NAMED INSURED", s["section_header"]))
    story.append(Spacer(1, 4))

    insured_name = (
        policy.insured_legal_name
        or (company.entity_legal_name if company else "")
        or "—"
    )
    insured_address_str = format_address(address) if address else "—"

    insured_pairs = [
        ("Named Insured:", insured_name),
        ("Business Address:", insured_address_str),
        (
            "Organization Type:",
            company.get_type_display()
            if company and hasattr(company, "get_type_display")
            else "—",
        ),
    ]
    story.append(_kv_table(insured_pairs, s))

    # ── Limits & Retentions ────────────────────────────────────────────
    story.append(Spacer(1, 6))
    story.append(Paragraph("COVERAGE LIMITS & RETENTIONS", s["section_header"]))
    story.append(Spacer(1, 4))

    limits = policy.limits_retentions or {}
    per_occ = policy.per_occurrence_limit or int(
        limits.get("per_occurrence_limit", limits.get("perOccurrenceLimit", 0))
    )
    agg = policy.aggregate_limit or int(
        limits.get("aggregate_limit", limits.get("aggregateLimit", 0))
    )
    retention = policy.retention or int(limits.get("retention", 0))

    limits_pairs = [
        ("Per Occurrence Limit:", f"${format_currency(per_occ)}" if per_occ else "—"),
        ("Aggregate Limit:", f"${format_currency(agg)}" if agg else "—"),
        (
            "Retention / Deductible:",
            f"${format_currency(retention)}" if retention else "—",
        ),
    ]
    if policy.retroactive_date:
        limits_pairs.append(
            ("Retroactive Date:", policy.retroactive_date.strftime("%B %d, %Y"))
        )
    story.append(_kv_table(limits_pairs, s))

    # ── Premium Breakdown ──────────────────────────────────────────────
    story.append(Spacer(1, 6))
    story.append(Paragraph("PREMIUM SUMMARY", s["section_header"]))
    story.append(Spacer(1, 4))

    annual_premium = Decimal(str(policy.premium))

    # Extract breakdown from rating result if available
    rating_result = quote.rating_result or {}
    coverage_result = rating_result.get(policy.coverage_type, {})
    base_premium = coverage_result.get("base_premium") or coverage_result.get(
        "basePremium"
    )
    state_tax = coverage_result.get("state_tax") or coverage_result.get("stateTax")
    stripe_fee = coverage_result.get("stripe_fee") or coverage_result.get("stripeFee")

    premium_rows = [
        [
            Paragraph("Description", s["table_header"]),
            Paragraph("Amount", s["table_header"]),
        ]
    ]
    if base_premium:
        premium_rows.append(
            [
                Paragraph("Base Premium", s["table_cell"]),
                Paragraph(f"${format_currency(float(base_premium))}", s["amount"]),
            ]
        )
    if state_tax:
        premium_rows.append(
            [
                Paragraph("State Tax", s["table_cell"]),
                Paragraph(f"${format_currency(float(state_tax))}", s["amount"]),
            ]
        )
    if stripe_fee:
        premium_rows.append(
            [
                Paragraph("Processing Fee", s["table_cell"]),
                Paragraph(f"${format_currency(float(stripe_fee))}", s["amount"]),
            ]
        )
    if policy.discount_percentage:
        disc = float(policy.discount_percentage)
        premium_rows.append(
            [
                Paragraph(f"Discount ({disc:.0f}%)", s["table_cell"]),
                Paragraph(
                    f"-${format_currency(float(annual_premium) * disc / 100)}",
                    s["amount"],
                ),
            ]
        )

    # Total
    premium_rows.append(
        [
            Paragraph("Annual Premium", s["table_header"]),
            Paragraph(f"${format_currency(float(annual_premium))}", s["amount"]),
        ]
    )
    if policy.billing_frequency == "monthly" and policy.monthly_premium:
        premium_rows.append(
            [
                Paragraph("Monthly Premium", s["table_cell"]),
                Paragraph(
                    f"${format_currency(float(policy.monthly_premium))}", s["amount"]
                ),
            ]
        )

    premium_table = Table(
        premium_rows,
        colWidths=[5.5 * inch, 1 * inch],
    )
    premium_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), CORGI_LIGHT_GREY),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, CORGI_BORDER),
                ("LINEABOVE", (0, -1), (-1, -1), 1, CORGI_DARK),
                ("BACKGROUND", (0, -1), (-1, -1), CORGI_LIGHT_GREY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (0, -1), 6),
                ("RIGHTPADDING", (-1, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(premium_table)

    # ── Quote Reference ────────────────────────────────────────────────
    story.append(Spacer(1, 10))
    story.append(
        HRFlowable(width="100%", thickness=0.5, color=CORGI_BORDER, spaceAfter=6)
    )
    story.append(
        Paragraph(
            f"Quote Number: {quote.quote_number}  |  Issued by: Corgi Insurance Services, Inc.  |  "
            f"Generated: {date.today().strftime('%B %d, %Y')}",
            s["footer"],
        )
    )
    story.append(
        Paragraph(
            "425 Bush St, STE 500, San Francisco, CA 94104  |  hello@corgi.insure  |  corgi.insure",
            s["footer"],
        )
    )
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "This declarations page is a summary of your insurance coverage. Please refer to your full "
            "policy document for complete terms, conditions, and exclusions.",
            s["footer"],
        )
    )

    doc.build(story)
    return buf.getvalue()
