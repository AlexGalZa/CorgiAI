"""
Embeddable Metrics Widgets API (V3 #49)

Lightweight JSON endpoints for embedding key metrics in Notion, Google Slides,
dashboards, or via iframe. Designed to be small and fast.

Auth:
    - Public metrics (GWP aggregate, policy count, loss ratio): no auth required
    - Sensitive metrics (ARR, cash position): requires API key auth

Endpoints:
    GET /api/v1/metrics/public     — Public metrics bundle (no auth)
    GET /api/v1/metrics/gwp        — Gross Written Premium (no auth)
    GET /api/v1/metrics/policy-count  — Active policy count (no auth)
    GET /api/v1/metrics/loss-ratio    — Loss ratio (no auth)
    GET /api/v1/metrics/sensitive  — Sensitive metrics bundle (API key required)
    GET /api/v1/metrics/arr        — ARR (API key required)
    GET /api/v1/metrics/embed/:metric  — iFrame-embeddable HTML card (no auth for public)
"""

from typing import Optional
from ninja import Router, Schema

from external_api.auth import ApiKeyAuth

# Two routers: one public, one authenticated
public_router = Router(tags=["Metrics Widgets"])
auth_router = Router(auth=ApiKeyAuth(), tags=["Metrics Widgets"])


# ─── Shared schemas ──────────────────────────────────────────────────────────


class GWPMetric(Schema):
    gwp_all_time: float
    gwp_ytd: float
    gwp_last_30_days: float
    growth_rate_pct: Optional[float] = None
    currency: str = "USD"


class PolicyCountMetric(Schema):
    active: int
    total: int


class LossRatioMetric(Schema):
    loss_ratio_pct: Optional[float] = None
    total_incurred: float
    total_earned: float


class ARRMetric(Schema):
    arr: float
    currency: str = "USD"


class PublicMetricsBundle(Schema):
    gwp: GWPMetric
    policy_count: PolicyCountMetric
    loss_ratio: LossRatioMetric
    generated_at: str


class SensitiveMetricsBundle(Schema):
    arr: ARRMetric
    cash_position: float
    generated_at: str


# ─── Public endpoints ────────────────────────────────────────────────────────


@public_router.get(
    "/public", response=PublicMetricsBundle, summary="Public metrics bundle"
)
def get_public_metrics(request):
    """
    Returns public-facing key metrics.

    No authentication required. Suitable for embedding in public dashboards,
    Notion databases, or Google Slides via data import.

    **Rate limit:** 60 req/min per IP (enforced at proxy layer).
    """
    from analytics.executive import get_executive_dashboard

    data = get_executive_dashboard()

    return PublicMetricsBundle(
        gwp=GWPMetric(
            gwp_all_time=data["gwp"]["all_time"],
            gwp_ytd=data["gwp"]["ytd"],
            gwp_last_30_days=data["gwp"]["last_30_days"],
            growth_rate_pct=data["growth_rate_pct"],
        ),
        policy_count=PolicyCountMetric(
            active=data["policy_count"]["active"],
            total=data["policy_count"]["total"],
        ),
        loss_ratio=LossRatioMetric(
            loss_ratio_pct=data["loss_ratio_pct"],
            total_incurred=data["claims"]["total_incurred"],
            total_earned=0.0,  # Not exposed publicly for competitive reasons
        ),
        generated_at=data["generated_at"],
    )


@public_router.get("/gwp", response=GWPMetric, summary="Gross Written Premium")
def get_gwp_metric(request):
    """Returns GWP metrics. No authentication required."""
    from analytics.executive import get_executive_dashboard

    data = get_executive_dashboard()
    return GWPMetric(
        gwp_all_time=data["gwp"]["all_time"],
        gwp_ytd=data["gwp"]["ytd"],
        gwp_last_30_days=data["gwp"]["last_30_days"],
        growth_rate_pct=data["growth_rate_pct"],
    )


@public_router.get(
    "/policy-count", response=PolicyCountMetric, summary="Active policy count"
)
def get_policy_count_metric(request):
    """Returns policy count. No authentication required."""
    from analytics.executive import get_executive_dashboard

    data = get_executive_dashboard()
    return PolicyCountMetric(
        active=data["policy_count"]["active"],
        total=data["policy_count"]["total"],
    )


@public_router.get("/loss-ratio", response=LossRatioMetric, summary="Loss ratio")
def get_loss_ratio_metric(request):
    """Returns loss ratio. No authentication required."""
    from analytics.executive import get_executive_dashboard

    data = get_executive_dashboard()
    return LossRatioMetric(
        loss_ratio_pct=data["loss_ratio_pct"],
        total_incurred=data["claims"]["total_incurred"],
        total_earned=0.0,
    )


@public_router.get("/embed/{metric}", summary="iFrame-embeddable metric card")
def get_embed_widget(request, metric: str):
    """
    Returns a self-contained HTML card for embedding in iframes.

    Supported metrics: `gwp`, `policy-count`, `loss-ratio`

    Example iframe:
    ```html
    <iframe src="https://api.corgiinsurance.com/api/v1/metrics/embed/gwp"
            width="280" height="120" frameborder="0"></iframe>
    ```
    """
    from django.http import HttpResponse
    from analytics.executive import get_executive_dashboard

    data = get_executive_dashboard()

    cards = {
        "gwp": {
            "label": "Gross Written Premium",
            "value": f"${data['gwp']['all_time']:,.0f}",
            "sub": f"YTD: ${data['gwp']['ytd']:,.0f}",
            "color": "#1f2937",
        },
        "policy-count": {
            "label": "Active Policies",
            "value": str(data["policy_count"]["active"]),
            "sub": f"{data['policy_count']['total']:,} total",
            "color": "#1f2937",
        },
        "loss-ratio": {
            "label": "Loss Ratio",
            "value": f"{data['loss_ratio_pct']}%"
            if data["loss_ratio_pct"] is not None
            else "—",
            "sub": "Incurred / Earned Premium",
            "color": (
                "#ef4444"
                if data["loss_ratio_pct"] and data["loss_ratio_pct"] > 100
                else "#f59e0b"
                if data["loss_ratio_pct"] and data["loss_ratio_pct"] > 70
                else "#10b981"
            ),
        },
    }

    card = cards.get(metric)
    if not card:
        return HttpResponse(
            "<p style='font-family:sans-serif;color:red'>Unknown metric</p>",
            content_type="text/html",
            status=400,
        )

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #ffffff;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      height: 100vh;
    }}
    .label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #6b7280;
      font-weight: 600;
    }}
    .value {{
      font-size: 28px;
      font-weight: 700;
      color: {card["color"]};
      margin-top: 6px;
      line-height: 1;
    }}
    .sub {{
      font-size: 12px;
      color: #9ca3af;
      margin-top: 6px;
    }}
    .brand {{
      font-size: 10px;
      color: #d1d5db;
      margin-top: 12px;
    }}
  </style>
</head>
<body>
  <div class="label">{card["label"]}</div>
  <div class="value">{card["value"]}</div>
  <div class="sub">{card["sub"]}</div>
  <div class="brand">Corgi Insurance</div>
</body>
</html>"""

    return HttpResponse(html, content_type="text/html")


# ─── Authenticated (sensitive) endpoints ────────────────────────────────────


@auth_router.get(
    "/sensitive",
    response=SensitiveMetricsBundle,
    summary="Sensitive metrics bundle (auth required)",
)
def get_sensitive_metrics(request):
    """
    Returns sensitive financial metrics.

    Requires a valid API key (`Authorization: Bearer cg_live_...`).
    """
    from analytics.executive import get_executive_dashboard

    data = get_executive_dashboard()
    return SensitiveMetricsBundle(
        arr=ARRMetric(arr=data["arr"]),
        cash_position=data["cash_position"],
        generated_at=data["generated_at"],
    )


@auth_router.get(
    "/arr", response=ARRMetric, summary="Annual Recurring Revenue (auth required)"
)
def get_arr_metric(request):
    """Returns ARR. Requires API key."""
    from analytics.executive import get_executive_dashboard

    data = get_executive_dashboard()
    return ARRMetric(arr=data["arr"])
