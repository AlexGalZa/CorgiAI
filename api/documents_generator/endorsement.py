"""
Endorsement Document Generator (V3 #63)

Generates a PDF endorsement document showing before/after changes for any
policy modification: limit changes, coverage additions/removals, name changes.
"""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal
from typing import Any

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

# Brand colours (shared palette)
CORGI_ORANGE = colors.HexColor("#FF5C00")
CORGI_DARK = colors.HexColor("#1D1D1D")
CORGI_GREY = colors.HexColor("#4E4E4E")
CORGI_LIGHT_GREY = colors.HexColor("#F5F6F7")
CORGI_BORDER = colors.HexColor("#D8DEE4")
CORGI_GREEN = colors.HexColor("#00B93B")
CORGI_RED = colors.HexColor("#EF4444")


def _styles():
    base = getSampleStyleSheet()
    s = {}
    s["title"] = ParagraphStyle(
        "title",
        parent=base["Normal"],
        fontSize=18,
        fontName="Helvetica-Bold",
        textColor=CORGI_DARK,
        spaceAfter=4,
    )
    s["subtitle"] = ParagraphStyle(
        "subtitle",
        parent=base["Normal"],
        fontSize=10,
        fontName="Helvetica",
        textColor=CORGI_GREY,
        spaceAfter=2,
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
    s["before"] = ParagraphStyle(
        "before",
        parent=base["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=CORGI_RED,
    )
    s["after"] = ParagraphStyle(
        "after",
        parent=base["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=CORGI_GREEN,
    )
    s["footer"] = ParagraphStyle(
        "footer",
        parent=base["Normal"],
        fontSize=7,
        fontName="Helvetica",
        textColor=CORGI_GREY,
        alignment=TA_CENTER,
    )
    s["badge_effective"] = ParagraphStyle(
        "badge_effective",
        parent=base["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=CORGI_ORANGE,
        spaceAfter=4,
    )
    return s


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


def _fmt_money(val) -> str:
    if val is None:
        return "—"
    try:
        return f"${format_currency(float(val))}"
    except (TypeError, ValueError):
        return str(val)


def generate_endorsement(policy, changes: dict[str, Any]) -> bytes:  # noqa: ANN001
    """Generate a PDF endorsement document showing before/after changes.

    Args:
        policy: A ``policies.models.Policy`` instance (the policy *before* changes).
        changes: Dict describing what changed. Supported keys:

            ``type`` (str): One of ``modify_limits``, ``add_coverage``,
                ``remove_coverage``, ``name_change``.

            ``effective_date`` (date | str): When the endorsement takes effect.

            ``new_premium`` (Decimal | float): New annual premium.

            ``reason`` (str): Human-readable reason for the change.

            ``new_limits`` (dict): For ``modify_limits`` — keys are limit names,
                values are ``{"before": x, "after": y}`` pairs.

            ``new_coverage_type`` (str): For ``add_coverage`` / ``remove_coverage``.

            ``name_change`` (dict): For ``name_change`` — ``{"before": "...", "after": "..."}``.

    Returns:
        PDF bytes.
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

    change_type = changes.get("type", "modification")
    change_type_display = {
        "modify_limits": "Limit Modification Endorsement",
        "add_coverage": "Coverage Addition Endorsement",
        "remove_coverage": "Coverage Removal Endorsement",
        "name_change": "Named Insured Change Endorsement",
    }.get(change_type, "Policy Endorsement")

    effective_date = changes.get("effective_date", date.today())
    if isinstance(effective_date, str):
        from datetime import datetime

        try:
            effective_date = datetime.fromisoformat(effective_date).date()
        except ValueError:
            effective_date = date.today()

    # ── Header ────────────────────────────────────────────────────────
    header_data = [
        [
            Paragraph("CORGI INSURANCE", s["title"]),
            Paragraph(change_type_display.upper(), s["title"]),
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

    story.append(
        Paragraph(
            f"⚡ Endorsement Effective Date: {effective_date.strftime('%B %d, %Y')}",
            s["badge_effective"],
        )
    )

    # ── Policy Details ────────────────────────────────────────────────
    story.append(Paragraph("POLICY INFORMATION", s["section_header"]))
    story.append(Spacer(1, 4))

    quote = policy.quote
    company = quote.company
    coverage_display = COVERAGE_DISPLAY_NAMES.get(
        policy.coverage_type, policy.coverage_type
    )

    policy_pairs = [
        ("Policy Number:", policy.policy_number),
        ("Coverage Type:", coverage_display),
        ("Named Insured:", company.entity_legal_name if company else "—"),
        ("Carrier:", policy.carrier),
        (
            "Policy Period:",
            (
                f"{policy.effective_date.strftime('%B %d, %Y')} – {policy.expiration_date.strftime('%B %d, %Y')}"
                if policy.effective_date and policy.expiration_date
                else "—"
            ),
        ),
        ("Endorsement Reason:", changes.get("reason", "—")),
    ]
    story.append(_kv_table(policy_pairs, s))

    # ── Change Details ─────────────────────────────────────────────────
    story.append(Spacer(1, 6))
    story.append(Paragraph("CHANGES — BEFORE AND AFTER", s["section_header"]))
    story.append(Spacer(1, 4))

    if change_type == "modify_limits":
        new_limits = changes.get("new_limits", {})
        rows = [
            [
                Paragraph("Item", s["table_header"]),
                Paragraph("Before", s["table_header"]),
                Paragraph("After", s["table_header"]),
            ]
        ]
        limit_labels = {
            "per_occurrence_limit": "Per Occurrence Limit",
            "aggregate_limit": "Aggregate Limit",
            "retention": "Retention / Deductible",
        }
        current_limits = policy.limits_retentions or {}
        for key, label in limit_labels.items():
            if key in new_limits:
                before_val = _fmt_money(
                    new_limits[key].get("before") or current_limits.get(key)
                )
                after_val = _fmt_money(new_limits[key].get("after"))
            else:
                before_val = _fmt_money(current_limits.get(key))
                after_val = before_val  # unchanged

            rows.append(
                [
                    Paragraph(label, s["table_cell"]),
                    Paragraph(
                        before_val,
                        s["before"] if key in new_limits else s["table_cell"],
                    ),
                    Paragraph(
                        after_val, s["after"] if key in new_limits else s["table_cell"]
                    ),
                ]
            )

        t = Table(rows, colWidths=[2.5 * inch, 2 * inch, 2 * inch])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), CORGI_LIGHT_GREY),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, CORGI_BORDER),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, CORGI_LIGHT_GREY],
                    ),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(t)

    elif change_type in ("add_coverage", "remove_coverage"):
        verb = "ADDED" if change_type == "add_coverage" else "REMOVED"
        new_cov = changes.get("new_coverage_type", "")
        cov_label = COVERAGE_DISPLAY_NAMES.get(new_cov, new_cov) if new_cov else "—"
        colour = s["after"] if change_type == "add_coverage" else s["before"]
        story.append(Paragraph(f"Coverage {verb}: {cov_label}", colour))

    elif change_type == "name_change":
        nc = changes.get("name_change", {})
        rows = [
            [
                Paragraph("Field", s["table_header"]),
                Paragraph("Before", s["table_header"]),
                Paragraph("After", s["table_header"]),
            ],
            [
                Paragraph("Named Insured", s["table_cell"]),
                Paragraph(nc.get("before", "—"), s["before"]),
                Paragraph(nc.get("after", "—"), s["after"]),
            ],
        ]
        t = Table(rows, colWidths=[2.5 * inch, 2 * inch, 2 * inch])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), CORGI_LIGHT_GREY),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, CORGI_BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(t)

    # ── Premium Impact ─────────────────────────────────────────────────
    old_premium = Decimal(str(policy.premium))
    new_premium = changes.get("new_premium")
    if new_premium is not None:
        new_premium = Decimal(str(new_premium))
        story.append(Spacer(1, 6))
        story.append(Paragraph("PREMIUM ADJUSTMENT", s["section_header"]))
        story.append(Spacer(1, 4))

        delta = new_premium - old_premium
        delta_label = (
            f"+${format_currency(float(abs(delta)))}"
            if delta >= 0
            else f"-${format_currency(float(abs(delta)))}"
        )
        delta_style = s["after"] if delta >= 0 else s["before"]

        prem_rows = [
            [
                Paragraph("Item", s["table_header"]),
                Paragraph("Amount", s["table_header"]),
            ],
            [
                Paragraph("Current Annual Premium", s["table_cell"]),
                Paragraph(f"${format_currency(float(old_premium))}", s["table_cell"]),
            ],
            [
                Paragraph("New Annual Premium", s["table_header"]),
                Paragraph(f"${format_currency(float(new_premium))}", s["table_header"]),
            ],
            [Paragraph("Change", s["table_cell"]), Paragraph(delta_label, delta_style)],
        ]

        if policy.billing_frequency == "monthly":
            monthly_factor = Decimal("1.111") / Decimal("12")
            new_monthly = (new_premium * monthly_factor).quantize(Decimal("0.01"))
            prem_rows.append(
                [
                    Paragraph("New Monthly Premium", s["table_cell"]),
                    Paragraph(
                        f"${format_currency(float(new_monthly))}", s["table_cell"]
                    ),
                ]
            )

        pt = Table(prem_rows, colWidths=[5.5 * inch, 1 * inch])
        pt.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), CORGI_LIGHT_GREY),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, CORGI_BORDER),
                    ("LINEABOVE", (0, 2), (-1, 2), 0.5, CORGI_BORDER),
                    ("BACKGROUND", (0, 2), (-1, 2), CORGI_LIGHT_GREY),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (-1, 0), (-1, -1), 6),
                    ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
                ]
            )
        )
        story.append(pt)

    # ── Footer ────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(
        HRFlowable(width="100%", thickness=0.5, color=CORGI_BORDER, spaceAfter=6)
    )
    story.append(
        Paragraph(
            f"Policy Number: {policy.policy_number}  |  Endorsement Effective: "
            f"{effective_date.strftime('%B %d, %Y')}  |  Generated: {date.today().strftime('%B %d, %Y')}",
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
            "This endorsement modifies the insurance policy described above. All other terms and conditions "
            "of the policy remain unchanged. This document must be attached to and forms part of the policy.",
            s["footer"],
        )
    )

    doc.build(story)
    return buf.getvalue()
