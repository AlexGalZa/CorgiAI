"""
Renewal Proposal Generator (V3 #65)

Generates a PDF renewal proposal comparing current policy terms against
proposed renewal terms. Includes current vs new premium, coverage comparison,
and any recommended changes.
"""

from __future__ import annotations

import io
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
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
from common.utils import format_currency

# Brand colours
CORGI_ORANGE = colors.HexColor("#FF5C00")
CORGI_DARK = colors.HexColor("#1D1D1D")
CORGI_GREY = colors.HexColor("#4E4E4E")
CORGI_LIGHT_GREY = colors.HexColor("#F5F6F7")
CORGI_BORDER = colors.HexColor("#D8DEE4")
CORGI_GREEN = colors.HexColor("#00B93B")
CORGI_BLUE = colors.HexColor("#1A73E8")


def _styles():
    base = getSampleStyleSheet()
    s = {}
    s["title"] = ParagraphStyle(
        "title",
        parent=base["Normal"],
        fontSize=20,
        fontName="Helvetica-Bold",
        textColor=CORGI_DARK,
        spaceAfter=4,
    )
    s["section_header"] = ParagraphStyle(
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
    s["label"] = ParagraphStyle(
        "label",
        parent=base["Normal"],
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=CORGI_GREY,
        spaceAfter=1,
    )
    s["value"] = ParagraphStyle(
        "value",
        parent=base["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=CORGI_DARK,
        spaceAfter=4,
    )
    s["table_header"] = ParagraphStyle(
        "table_header",
        parent=base["Normal"],
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=CORGI_GREY,
    )
    s["table_cell"] = ParagraphStyle(
        "table_cell",
        parent=base["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=CORGI_DARK,
    )
    s["current"] = ParagraphStyle(
        "current",
        parent=base["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=CORGI_GREY,
    )
    s["renewal"] = ParagraphStyle(
        "renewal",
        parent=base["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=CORGI_DARK,
    )
    s["highlight"] = ParagraphStyle(
        "highlight",
        parent=base["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=CORGI_ORANGE,
    )
    s["recommend"] = ParagraphStyle(
        "recommend",
        parent=base["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=CORGI_BLUE,
        leftIndent=12,
        spaceAfter=3,
    )
    s["footer"] = ParagraphStyle(
        "footer",
        parent=base["Normal"],
        fontSize=7,
        fontName="Helvetica",
        textColor=CORGI_GREY,
        alignment=TA_CENTER,
    )
    return s


def _fmt_money(val) -> str:
    if val is None:
        return "—"
    try:
        return f"${format_currency(float(val))}"
    except (TypeError, ValueError):
        return str(val)


def _kv_table(pairs, s):
    data = [[Paragraph(k, s["label"]), Paragraph(v, s["value"])] for k, v in pairs]
    t = Table(data, colWidths=[2 * inch, 4.5 * inch])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return t


def _build_renewal_limits(policy) -> dict:  # noqa: ANN001
    """Pull current limits from policy model, return as dict."""
    limits = policy.limits_retentions or {}
    return {
        "per_occurrence_limit": policy.per_occurrence_limit
        or int(limits.get("per_occurrence_limit", limits.get("perOccurrenceLimit", 0))),
        "aggregate_limit": policy.aggregate_limit
        or int(limits.get("aggregate_limit", limits.get("aggregateLimit", 0))),
        "retention": policy.retention or int(limits.get("retention", 0)),
    }


def _generate_recommendations(
    policy, renewal_premium: Decimal, current_premium: Decimal
) -> list[str]:
    """Generate recommended changes based on policy data."""
    recs = []
    pct_change = (
        float((renewal_premium - current_premium) / current_premium * 100)
        if current_premium
        else 0
    )
    if pct_change > 10:
        recs.append(
            f"Premium increase of {pct_change:.1f}% — consider bundling additional coverages for potential multi-policy discount."
        )
    elif pct_change < -5:
        recs.append(
            f"Premium decrease of {abs(pct_change):.1f}% reflects improved risk profile."
        )

    limits = _build_renewal_limits(policy)
    if limits["aggregate_limit"] < 2_000_000:
        recs.append(
            "Consider increasing aggregate limit to $2,000,000 for broader protection."
        )
    if limits["retention"] > 25_000:
        recs.append(
            "High retention may expose insured to significant out-of-pocket costs per claim."
        )

    quote = policy.quote
    company = quote.company if quote else None
    if (
        company
        and company.last_12_months_revenue
        and company.last_12_months_revenue > 5_000_000
    ):
        if limits["aggregate_limit"] < 3_000_000:
            recs.append(
                "Given revenue growth, consider increasing limits to $3,000,000 or higher."
            )

    if not recs:
        recs.append(
            "No significant changes recommended — coverage appears well-matched to current risk profile."
        )

    return recs


def generate_renewal_proposal(
    policy, renewal_premium: Optional[Decimal] = None
) -> bytes:  # noqa: ANN001
    """Generate a PDF renewal proposal for the given Policy.

    Args:
        policy: A ``policies.models.Policy`` instance (the expiring/current policy).
        renewal_premium: Optional proposed renewal premium. If omitted, the
            current premium is used as the renewal benchmark (flat renewal).

    Returns:
        PDF bytes of the renewal proposal.
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

    current_premium = Decimal(str(policy.premium))
    if renewal_premium is None:
        renewal_premium = current_premium
    else:
        renewal_premium = Decimal(str(renewal_premium))

    renewal_effective = (
        policy.expiration_date if policy.expiration_date else date.today()
    )
    renewal_expiration = renewal_effective + timedelta(days=365)

    # ── Header ────────────────────────────────────────────────────────
    header_data = [
        [
            Paragraph("CORGI INSURANCE", s["title"]),
            Paragraph("RENEWAL PROPOSAL", s["title"]),
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

    quote = policy.quote
    company = quote.company
    coverage_display = COVERAGE_DISPLAY_NAMES.get(
        policy.coverage_type, policy.coverage_type
    )

    # ── Insured & Policy Info ──────────────────────────────────────────
    story.append(Paragraph("INSURED & POLICY INFORMATION", s["section_header"]))
    story.append(Spacer(1, 4))
    story.append(
        _kv_table(
            [
                ("Named Insured:", company.entity_legal_name if company else "—"),
                ("Policy Number:", policy.policy_number),
                ("Coverage Type:", coverage_display),
                ("Carrier:", policy.carrier),
                ("Prepared:", date.today().strftime("%B %d, %Y")),
            ],
            s,
        )
    )

    # ── Term Comparison ───────────────────────────────────────────────
    story.append(Spacer(1, 6))
    story.append(Paragraph("POLICY TERM COMPARISON", s["section_header"]))
    story.append(Spacer(1, 4))

    term_rows = [
        [
            Paragraph("", s["table_header"]),
            Paragraph("Current Policy", s["table_header"]),
            Paragraph("Proposed Renewal", s["table_header"]),
        ],
        [
            Paragraph("Effective Date", s["table_cell"]),
            Paragraph(
                policy.effective_date.strftime("%m/%d/%Y")
                if policy.effective_date
                else "—",
                s["current"],
            ),
            Paragraph(renewal_effective.strftime("%m/%d/%Y"), s["renewal"]),
        ],
        [
            Paragraph("Expiration Date", s["table_cell"]),
            Paragraph(
                policy.expiration_date.strftime("%m/%d/%Y")
                if policy.expiration_date
                else "—",
                s["current"],
            ),
            Paragraph(renewal_expiration.strftime("%m/%d/%Y"), s["renewal"]),
        ],
    ]

    limits = _build_renewal_limits(policy)
    limit_labels = [
        ("per_occurrence_limit", "Per Occurrence Limit"),
        ("aggregate_limit", "Aggregate Limit"),
        ("retention", "Retention"),
    ]
    for key, label in limit_labels:
        val = limits[key]
        term_rows.append(
            [
                Paragraph(label, s["table_cell"]),
                Paragraph(_fmt_money(val), s["current"]),
                Paragraph(_fmt_money(val), s["renewal"]),  # same unless changed
            ]
        )

    term_t = Table(term_rows, colWidths=[2 * inch, 2.25 * inch, 2.25 * inch])
    term_t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), CORGI_LIGHT_GREY),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, CORGI_BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CORGI_LIGHT_GREY]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(term_t)

    # ── Premium Comparison ─────────────────────────────────────────────
    story.append(Spacer(1, 6))
    story.append(Paragraph("PREMIUM COMPARISON", s["section_header"]))
    story.append(Spacer(1, 4))

    delta = renewal_premium - current_premium
    pct = float(delta / current_premium * 100) if current_premium else 0
    pct_str = f"+{pct:.1f}%" if pct >= 0 else f"{pct:.1f}%"

    prem_rows = [
        [
            Paragraph("", s["table_header"]),
            Paragraph("Current", s["table_header"]),
            Paragraph("Proposed Renewal", s["table_header"]),
            Paragraph("Change", s["table_header"]),
        ],
        [
            Paragraph("Annual Premium", s["table_cell"]),
            Paragraph(_fmt_money(current_premium), s["current"]),
            Paragraph(_fmt_money(renewal_premium), s["renewal"]),
            Paragraph(pct_str, s["highlight"]),
        ],
    ]

    if policy.billing_frequency == "monthly":
        current_monthly = (current_premium * Decimal("1.111") / 12).quantize(
            Decimal("0.01")
        )
        renewal_monthly = (renewal_premium * Decimal("1.111") / 12).quantize(
            Decimal("0.01")
        )
        monthly_delta = renewal_monthly - current_monthly
        prem_rows.append(
            [
                Paragraph("Monthly Premium", s["table_cell"]),
                Paragraph(_fmt_money(current_monthly), s["current"]),
                Paragraph(_fmt_money(renewal_monthly), s["renewal"]),
                Paragraph(
                    f"+{_fmt_money(monthly_delta)}"
                    if monthly_delta >= 0
                    else _fmt_money(monthly_delta),
                    s["highlight"],
                ),
            ]
        )

    prem_t = Table(prem_rows, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch, 1 * inch])
    prem_t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), CORGI_LIGHT_GREY),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, CORGI_BORDER),
                ("LINEABOVE", (0, 1), (-1, 1), 0.5, CORGI_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(prem_t)

    # ── Recommended Changes ────────────────────────────────────────────
    story.append(Spacer(1, 6))
    story.append(Paragraph("RECOMMENDATIONS", s["section_header"]))
    story.append(Spacer(1, 4))

    recommendations = _generate_recommendations(
        policy, renewal_premium, current_premium
    )
    for i, rec in enumerate(recommendations, start=1):
        story.append(Paragraph(f"{i}. {rec}", s["recommend"]))

    # ── Footer ────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(
        HRFlowable(width="100%", thickness=0.5, color=CORGI_BORDER, spaceAfter=6)
    )
    story.append(
        Paragraph(
            f"Policy: {policy.policy_number}  |  Renewal Effective: {renewal_effective.strftime('%B %d, %Y')}  "
            f"|  Generated: {date.today().strftime('%B %d, %Y')}",
            s["footer"],
        )
    )
    story.append(
        Paragraph(
            "Corgi Insurance Services, Inc.  |  425 Bush St, STE 500, San Francisco, CA 94104  |  hello@corgi.insure",
            s["footer"],
        )
    )
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "This renewal proposal is subject to underwriting review and final approval. Premiums are estimates "
            "only and may change based on updated risk information. Coverage terms are subject to the full "
            "policy wording, terms, conditions, and exclusions.",
            s["footer"],
        )
    )

    doc.build(story)
    return buf.getvalue()
