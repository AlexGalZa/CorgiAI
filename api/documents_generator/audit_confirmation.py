"""
Audit Confirmation Letter generator for the Corgi Insurance platform.

Generates a PDF confirming policy details for auditor requests.
Includes: carrier, limits, premium, effective dates, insured name.
"""

from io import BytesIO

import fitz  # PyMuPDF


# ── Layout constants ──────────────────────────────────────────────────────────
PAGE_W, PAGE_H = 612, 792  # US Letter
MARGIN = 72
LINE_HEIGHT = 16
SMALL = 9
NORMAL = 10
HEADER = 13
TITLE = 18

CORGI_ORANGE = (1.0, 0.36, 0.0)
DARK = (0.11, 0.11, 0.11)
GRAY = (0.45, 0.45, 0.45)
LIGHT_GRAY = (0.95, 0.95, 0.95)
MID_GRAY = (0.75, 0.75, 0.75)


def _text(
    page, text: str, x: float, y: float, size: float, color=DARK, bold: bool = False
):
    page.insert_text(
        fitz.Point(x, y),
        text,
        fontname="helv-bold" if bold else "helv",
        fontsize=size,
        color=color,
    )


def _hline(page, x1: float, x2: float, y: float, width: float = 0.5, color=MID_GRAY):
    page.draw_line(fitz.Point(x1, y), fitz.Point(x2, y), color=color, width=width)


def _rect(
    page, x1: float, y1: float, x2: float, y2: float, fill=LIGHT_GRAY, color=None
):
    page.draw_rect(fitz.Rect(x1, y1, x2, y2), color=color, fill=fill)


def _fmt_currency(value) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
        if v >= 1_000_000:
            return f"${v / 1_000_000:,.1f}M"
        return f"${v:,.0f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_date(d) -> str:
    if d is None:
        return "—"
    try:
        return d.strftime("%B %d, %Y")
    except Exception:
        return str(d)


def _label_value(
    page, label: str, value: str, x: float, y: float, label_w: float = 160
):
    _text(page, label, x, y, NORMAL, color=GRAY)
    _text(page, value, x + label_w, y, NORMAL, bold=False)


def generate_audit_confirmation(policy) -> bytes:
    """
    Generate an audit confirmation letter PDF for the given policy.

    Args:
        policy: A Policy model instance.

    Returns:
        PDF bytes.
    """

    quote = policy.quote
    company = quote.company if quote else None
    insured_name = getattr(company, "entity_legal_name", None) or (
        getattr(company, "business_description", "")[:60] if company else "Unknown"
    )

    limits_data = policy.limits_retentions or {}
    per_occurrence = policy.per_occurrence_limit or int(
        limits_data.get("per_occurrence_limit")
        or limits_data.get("perOccurrenceLimit")
        or 0
    )
    aggregate = policy.aggregate_limit or int(
        limits_data.get("aggregate_limit") or limits_data.get("aggregateLimit") or 0
    )
    retention = policy.retention or int(limits_data.get("retention") or 0)
    premium = getattr(policy, "premium", None) or float(
        limits_data.get("premium", 0) or 0
    )

    carrier = getattr(policy, "carrier", "") or "See Policy Declarations"
    coverage_display = (
        (policy.coverage_type or "").replace("-", " ").title()
        if policy.coverage_type
        else "Commercial Insurance"
    )

    today = __import__("datetime").date.today()

    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    y = MARGIN

    # ── Letterhead ────────────────────────────────────────────────────────────
    _text(
        page,
        "CORGI INSURANCE SERVICES, INC.",
        MARGIN,
        y,
        HEADER,
        bold=True,
        color=CORGI_ORANGE,
    )
    y += LINE_HEIGHT
    _text(
        page,
        "425 Bush St, STE 500  ·  San Francisco, CA 94104",
        MARGIN,
        y,
        SMALL,
        color=GRAY,
    )
    y += LINE_HEIGHT - 2
    _text(
        page,
        "Tel: 1 850 662 6744  ·  hello@corgi.insure  ·  corgi.insure",
        MARGIN,
        y,
        SMALL,
        color=GRAY,
    )
    y += LINE_HEIGHT + 4
    _hline(page, MARGIN, PAGE_W - MARGIN, y, width=1.5, color=CORGI_ORANGE)
    y += 22

    # ── Date line ─────────────────────────────────────────────────────────────
    _text(page, _fmt_date(today), MARGIN, y, NORMAL, color=GRAY)
    y += LINE_HEIGHT * 2

    # ── RE line ───────────────────────────────────────────────────────────────
    _text(
        page,
        "RE: Confirmation of Insurance / Audit Verification",
        MARGIN,
        y,
        NORMAL,
        bold=True,
    )
    y += LINE_HEIGHT
    _text(page, f"Policy Number: {policy.policy_number}", MARGIN, y, NORMAL)
    y += LINE_HEIGHT * 2

    # ── Body text ─────────────────────────────────────────────────────────────
    _text(page, "To Whom It May Concern:", MARGIN, y, NORMAL)
    y += LINE_HEIGHT * 1.5

    body_text = (
        "This letter confirms the existence and terms of the insurance policy referenced above. "
        "The policy was issued by Corgi Insurance Services, Inc. on behalf of the carrier identified below. "
        "The information provided herein is accurate as of the date of this letter."
    )
    # Simple word-wrap
    words = body_text.split()
    line_buf = ""
    max_w = PAGE_W - 2 * MARGIN
    for word in words:
        test = (line_buf + " " + word).strip()
        # Approximate: ~6 pts per char at 10pt
        if len(test) * 5.5 > max_w:
            _text(page, line_buf, MARGIN, y, NORMAL)
            y += LINE_HEIGHT
            line_buf = word
        else:
            line_buf = test
    if line_buf:
        _text(page, line_buf, MARGIN, y, NORMAL)
        y += LINE_HEIGHT

    y += LINE_HEIGHT

    # ── Policy details box ────────────────────────────────────────────────────
    box_top = y - 8
    _rect(
        page,
        MARGIN - 8,
        box_top,
        PAGE_W - MARGIN + 8,
        box_top + 14 + 10 * (LINE_HEIGHT + 4) + 16,
        fill=LIGHT_GRAY,
    )

    _text(page, "POLICY DETAILS", MARGIN, y, HEADER, bold=True, color=DARK)
    y += LINE_HEIGHT + 8

    details = [
        ("Insured Name:", insured_name),
        ("Policy Number:", policy.policy_number),
        ("Coverage Type:", coverage_display),
        ("Carrier:", carrier),
        ("Effective Date:", _fmt_date(policy.effective_date)),
        ("Expiration Date:", _fmt_date(policy.expiration_date)),
        (
            "Per Occurrence / Per Claim Limit:",
            _fmt_currency(per_occurrence) if per_occurrence else "—",
        ),
        ("Aggregate Limit:", _fmt_currency(aggregate) if aggregate else "—"),
        ("Retention / Deductible:", _fmt_currency(retention) if retention else "—"),
        ("Annual Premium:", _fmt_currency(premium) if premium else "—"),
    ]

    for label, value in details:
        _label_value(page, label, value, MARGIN, y, label_w=200)
        y += LINE_HEIGHT + 4

    y += 8  # bottom padding for box
    y += LINE_HEIGHT * 2

    # ── Notes ─────────────────────────────────────────────────────────────────
    note_lines = [
        "This confirmation is issued as a matter of information only and confers no rights upon the auditor",
        "or any other party. This confirmation does not amend, extend, or alter the coverage afforded by",
        "the policy described above. All coverage is subject to the terms and conditions of the policy.",
    ]
    for note in note_lines:
        _text(page, note, MARGIN, y, SMALL, color=GRAY)
        y += LINE_HEIGHT - 2

    y += LINE_HEIGHT * 2

    # ── Signature block ───────────────────────────────────────────────────────
    _hline(page, MARGIN, MARGIN + 200, y)
    y += LINE_HEIGHT
    _text(page, "Authorized Representative", MARGIN, y, NORMAL)
    y += LINE_HEIGHT
    _text(page, "Corgi Insurance Services, Inc.", MARGIN, y, NORMAL, color=GRAY)

    # ── Footer ────────────────────────────────────────────────────────────────
    _hline(page, MARGIN, PAGE_W - MARGIN, PAGE_H - MARGIN + 5)
    page.insert_text(
        fitz.Point(MARGIN, PAGE_H - MARGIN + 18),
        f"Policy {policy.policy_number}  ·  Corgi Insurance Services, Inc.  ·  AUDIT CONFIRMATION",
        fontname="helv",
        fontsize=7,
        color=GRAY,
    )
    page.insert_text(
        fitz.Point(PAGE_W - MARGIN - 60, PAGE_H - MARGIN + 18),
        "Page 1 of 1",
        fontname="helv",
        fontsize=7,
        color=GRAY,
    )

    buf = BytesIO()
    doc.save(buf, garbage=3, deflate=True)
    doc.close()
    return buf.getvalue()
