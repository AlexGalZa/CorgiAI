"""
Loss Run Report generator for the Corgi Insurance platform.

Generates a PDF loss run showing all claims by policy for a given organization.
Standard broker/carrier format: claim date, description, amount paid,
amount reserved, status.
"""

from io import BytesIO

import fitz  # PyMuPDF


# ── Layout constants ──────────────────────────────────────────────────────────
PAGE_W, PAGE_H = 612, 792  # US Letter (points)
MARGIN = 50
LINE_HEIGHT = 14
SMALL = 9
NORMAL = 10
HEADER = 12
TITLE = 16
SECTION = 13

CORGI_ORANGE = (1.0, 0.36, 0.0)  # #ff5c00
DARK = (0.11, 0.11, 0.11)  # #1c1c1c
GRAY = (0.4, 0.4, 0.4)
LIGHT_GRAY = (0.95, 0.95, 0.95)
MID_GRAY = (0.85, 0.85, 0.85)


def _fmt_currency(value) -> str:
    if value is None:
        return "—"
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_date(d) -> str:
    if d is None:
        return "—"
    try:
        return d.strftime("%m/%d/%Y")
    except Exception:
        return str(d)


def _text(
    page, text: str, x: float, y: float, size: float, color=DARK, bold: bool = False
):
    font = "helv-bold" if bold else "helv"
    page.insert_text(
        fitz.Point(x, y),
        text,
        fontname=font,
        fontsize=size,
        color=color,
    )


def _hline(page, x1: float, x2: float, y: float, width: float = 0.5, color=MID_GRAY):
    page.draw_line(fitz.Point(x1, y), fitz.Point(x2, y), color=color, width=width)


def _rect(page, x1: float, y1: float, x2: float, y2: float, fill=LIGHT_GRAY):
    page.draw_rect(fitz.Rect(x1, y1, x2, y2), color=None, fill=fill)


def generate_loss_run(organization) -> bytes:
    """
    Generate a loss run PDF for the given organization.

    Args:
        organization: An Organization model instance.

    Returns:
        PDF bytes.
    """
    from claims.models import Claim
    from policies.models import Policy

    org_name = organization.name
    generated_date = __import__("datetime").date.today()

    # Gather all policies for the org's quotes/users
    policies = (
        Policy.objects.filter(quote__organization=organization)
        .select_related("quote", "quote__company")
        .order_by("policy_number")
    )

    # Build policy → claims map
    policy_claims = {}
    for policy in policies:
        claims_qs = Claim.objects.filter(policy=policy).order_by(
            "incident_date", "created_at"
        )
        policy_claims[policy.pk] = list(claims_qs)

    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    y = MARGIN

    # ── Header ───────────────────────────────────────────────────────────────
    _rect(page, MARGIN, y, PAGE_W - MARGIN, y + 56, fill=CORGI_ORANGE)
    page.insert_text(
        fitz.Point(MARGIN + 12, y + 22),
        "CORGI INSURANCE SERVICES, INC.",
        fontname="helv-bold",
        fontsize=HEADER,
        color=(1, 1, 1),
    )
    page.insert_text(
        fitz.Point(MARGIN + 12, y + 40),
        "Loss Run Report",
        fontname="helv",
        fontsize=NORMAL,
        color=(1, 1, 1),
    )
    page.insert_text(
        fitz.Point(PAGE_W - MARGIN - 140, y + 22),
        f"Generated: {_fmt_date(generated_date)}",
        fontname="helv",
        fontsize=SMALL,
        color=(1, 1, 1),
    )

    y += 72

    # ── Insured info block ────────────────────────────────────────────────────
    _text(page, "INSURED:", MARGIN, y, SMALL, color=GRAY)
    _text(page, org_name, MARGIN + 55, y, NORMAL, bold=True)
    y += LINE_HEIGHT + 4
    _hline(page, MARGIN, PAGE_W - MARGIN, y)
    y += 10

    # ── Totals summary ────────────────────────────────────────────────────────
    all_claims = [c for claims in policy_claims.values() for c in claims]
    total_paid = sum(
        (float(c.paid_loss or 0) + float(c.paid_lae or 0)) for c in all_claims
    )
    total_reserved = sum(
        (float(c.case_reserve_loss or 0) + float(c.case_reserve_lae or 0))
        for c in all_claims
    )
    open_claims = sum(
        1 for c in all_claims if c.status in ("submitted", "under_review", "approved")
    )
    closed_claims = sum(1 for c in all_claims if c.status in ("denied", "closed"))

    _text(page, "SUMMARY", MARGIN, y, HEADER, bold=True)
    y += LINE_HEIGHT + 4

    summary_cols = [
        ("Total Policies", str(len(policies))),
        ("Total Claims", str(len(all_claims))),
        ("Open Claims", str(open_claims)),
        ("Closed Claims", str(closed_claims)),
        ("Total Paid (Loss+LAE)", _fmt_currency(total_paid)),
        ("Total Reserved", _fmt_currency(total_reserved)),
        ("Total Incurred", _fmt_currency(total_paid + total_reserved)),
    ]

    col_w = (PAGE_W - 2 * MARGIN) / 4
    for idx, (label, value) in enumerate(summary_cols):
        col = idx % 4
        row = idx // 4
        cx = MARGIN + col * col_w
        cy = y + row * (LINE_HEIGHT * 2 + 4)
        _rect(
            page, cx + 2, cy - LINE_HEIGHT + 2, cx + col_w - 4, cy + 6, fill=LIGHT_GRAY
        )
        _text(page, label, cx + 6, cy - 2, SMALL, color=GRAY)
        _text(page, value, cx + 6, cy + 10, NORMAL, bold=True)

    rows_used = (len(summary_cols) + 3) // 4
    y += rows_used * (LINE_HEIGHT * 2 + 4) + 16
    _hline(page, MARGIN, PAGE_W - MARGIN, y, width=1.0, color=CORGI_ORANGE)
    y += 14

    # ── Per-policy detail ─────────────────────────────────────────────────────
    # claim detail columns: date, description, paid_loss, paid_lae, reserved, status
    claim_col_x = [
        MARGIN + 20,
        MARGIN + 100,
        MARGIN + 240,
        MARGIN + 315,
        MARGIN + 390,
        MARGIN + 465,
    ]
    claim_col_headers = [
        "Incident Date",
        "Description",
        "Paid Loss",
        "Paid LAE",
        "Reserved",
        "Status",
    ]

    def check_page_overflow(cur_y: float, need: float = 60) -> tuple[fitz.Page, float]:
        nonlocal doc
        if cur_y + need > PAGE_H - MARGIN:
            pg = doc.new_page(width=PAGE_W, height=PAGE_H)
            _text(
                pg,
                f"Loss Run — {org_name} (continued)",
                MARGIN,
                MARGIN - 5,
                SMALL,
                color=GRAY,
            )
            _hline(pg, MARGIN, PAGE_W - MARGIN, MARGIN + 2)
            return pg, MARGIN + 18
        return page, cur_y

    if not policies:
        _text(
            page,
            "No policies found for this organization.",
            MARGIN,
            y,
            NORMAL,
            color=GRAY,
        )
        y += LINE_HEIGHT * 3
    else:
        for policy in policies:
            page, y = check_page_overflow(y, 80)
            claims = policy_claims.get(policy.pk, [])

            # Policy header row
            _rect(page, MARGIN, y - 11, PAGE_W - MARGIN, y + 5, fill=(0.93, 0.93, 0.93))
            _text(
                page,
                f"Policy: {policy.policy_number}",
                MARGIN + 4,
                y,
                NORMAL,
                bold=True,
            )
            _text(page, policy.coverage_type or "—", MARGIN + 180, y, NORMAL)
            eff = _fmt_date(policy.effective_date)
            exp = _fmt_date(policy.expiration_date)
            _text(page, f"{eff} – {exp}", MARGIN + 310, y, NORMAL)
            _text(page, f"Status: {policy.status or '—'}", MARGIN + 440, y, NORMAL)
            y += LINE_HEIGHT + 6

            if not claims:
                _text(
                    page,
                    "  No claims on this policy.",
                    MARGIN + 20,
                    y,
                    SMALL,
                    color=GRAY,
                )
                y += LINE_HEIGHT + 8
                _hline(page, MARGIN, PAGE_W - MARGIN, y)
                y += 8
                continue

            # Claim table header
            _rect(page, MARGIN + 20, y - 10, PAGE_W - MARGIN, y + 4, fill=LIGHT_GRAY)
            for i, (header, cx) in enumerate(zip(claim_col_headers, claim_col_x)):
                _text(page, header, cx, y, SMALL, bold=True, color=GRAY)
            y += LINE_HEIGHT + 4

            # Claim rows
            policy_total_paid = 0.0
            policy_total_reserved = 0.0
            for claim in claims:
                page, y = check_page_overflow(y, LINE_HEIGHT + 6)

                paid_loss = float(claim.paid_loss or 0)
                paid_lae = float(claim.paid_lae or 0)
                reserved = float(claim.case_reserve_loss or 0) + float(
                    claim.case_reserve_lae or 0
                )
                policy_total_paid += paid_loss + paid_lae
                policy_total_reserved += reserved

                desc_short = (claim.description or "")[:55]
                if len(claim.description or "") > 55:
                    desc_short += "…"

                row_vals = [
                    _fmt_date(claim.incident_date or claim.created_at),
                    desc_short,
                    _fmt_currency(paid_loss),
                    _fmt_currency(paid_lae),
                    _fmt_currency(reserved),
                    claim.status or "—",
                ]
                for val, cx in zip(row_vals, claim_col_x):
                    _text(page, val, cx, y, SMALL)
                y += LINE_HEIGHT + 2
                _hline(page, MARGIN + 20, PAGE_W - MARGIN, y, width=0.3)
                y += 4

            # Policy subtotal
            _text(page, "Policy Total:", MARGIN + 160, y, SMALL, bold=True)
            _text(
                page,
                _fmt_currency(policy_total_paid),
                claim_col_x[2],
                y,
                SMALL,
                bold=True,
            )
            _text(
                page,
                _fmt_currency(policy_total_reserved),
                claim_col_x[4],
                y,
                SMALL,
                bold=True,
            )
            y += LINE_HEIGHT + 4
            _hline(page, MARGIN, PAGE_W - MARGIN, y, width=0.7)
            y += 12

    # ── Footer on last page ───────────────────────────────────────────────────
    _hline(page, MARGIN, PAGE_W - MARGIN, PAGE_H - MARGIN + 5)
    page.insert_text(
        fitz.Point(MARGIN, PAGE_H - MARGIN + 18),
        "Corgi Insurance Services, Inc.  ·  425 Bush St, STE 500, San Francisco, CA 94104  ·  hello@corgi.insure",
        fontname="helv",
        fontsize=7,
        color=GRAY,
    )
    page.insert_text(
        fitz.Point(PAGE_W - MARGIN - 100, PAGE_H - MARGIN + 18),
        "CONFIDENTIAL — LOSS RUN",
        fontname="helv",
        fontsize=7,
        color=GRAY,
    )

    buf = BytesIO()
    doc.save(buf, garbage=3, deflate=True)
    doc.close()
    return buf.getvalue()
