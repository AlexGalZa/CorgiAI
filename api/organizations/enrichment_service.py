"""
Company data enrichment service for the Corgi Insurance platform.

Provides a unified interface for enriching company data from external providers
(Clearbit, Crunchbase, etc.). Currently uses a stub implementation that returns
None, ready for real provider integration.

Usage:
    from organizations.enrichment_service import CompanyEnrichmentService

    data = CompanyEnrichmentService.enrich("Acme Corp")
    if data:
        company.update_from_enrichment(data)
"""

import logging

logger = logging.getLogger(__name__)


class EnrichmentResult:
    """Structured result from company enrichment."""

    def __init__(
        self,
        revenue: int | None = None,
        employee_count: int | None = None,
        industry: str | None = None,
        description: str | None = None,
        founded_year: int | None = None,
        website: str | None = None,
        source: str | None = None,
    ):
        self.revenue = revenue
        self.employee_count = employee_count
        self.industry = industry
        self.description = description
        self.founded_year = founded_year
        self.website = website
        self.source = source

    def to_dict(self) -> dict:
        return {
            "revenue": self.revenue,
            "employee_count": self.employee_count,
            "industry": self.industry,
            "description": self.description,
            "founded_year": self.founded_year,
            "website": self.website,
            "source": self.source,
        }


class CompanyEnrichmentService:
    """
    Service for enriching company data from external providers.

    Interface:
        enrich(company_name: str) -> dict | None

    Returns a dict with the following keys (all optional/None if unavailable):
        - revenue (int): Annual revenue in USD
        - employee_count (int): Number of employees
        - industry (str): Industry / sector
        - description (str): Company description
        - founded_year (int): Year founded
        - website (str): Company website URL
        - source (str): Which provider returned the data

    Returns None if enrichment is unavailable or the company is not found.

    To plug in a real provider:
        1. Add provider credentials to settings (CLEARBIT_API_KEY, etc.)
        2. Implement _enrich_via_clearbit() or _enrich_via_crunchbase()
        3. Call the provider from enrich() with a try/except fallback
    """

    @staticmethod
    def enrich(company_name: str) -> dict | None:
        """
        Enrich company data by name.

        Args:
            company_name: Legal name or DBA of the company to look up.

        Returns:
            dict with enrichment data, or None if not found / provider unavailable.
        """
        if not company_name or not company_name.strip():
            return None

        # ------------------------------------------------------------------ #
        # STUB: Replace the body below with a real provider call.             #
        #                                                                     #
        # Example Clearbit integration:                                       #
        #   result = CompanyEnrichmentService._enrich_via_clearbit(company_name) #
        #   if result:                                                        #
        #       return result.to_dict()                                       #
        #                                                                     #
        # Example Crunchbase integration:                                     #
        #   result = CompanyEnrichmentService._enrich_via_crunchbase(company_name) #
        #   if result:                                                        #
        #       return result.to_dict()                                       #
        # ------------------------------------------------------------------ #

        logger.debug(
            "Company enrichment stub called for '%s' — no provider configured",
            company_name,
        )
        return None

    # ------------------------------------------------------------------ #
    # Provider stubs — implement and wire up when credentials are ready   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _enrich_via_clearbit(company_name: str) -> EnrichmentResult | None:
        """
        Enrich via Clearbit Enrichment API.

        Requires: CLEARBIT_API_KEY in settings.
        Docs: https://dashboard.clearbit.com/docs#enrichment-api-company-api
        """
        # import clearbit
        # from django.conf import settings
        # clearbit.key = settings.CLEARBIT_API_KEY
        # company = clearbit.Company.find(name=company_name, stream=True)
        # if not company:
        #     return None
        # return EnrichmentResult(
        #     revenue=company.get('metrics', {}).get('annualRevenue'),
        #     employee_count=company.get('metrics', {}).get('employees'),
        #     industry=company.get('category', {}).get('industry'),
        #     description=company.get('description'),
        #     founded_year=company.get('foundedYear'),
        #     website=company.get('domain'),
        #     source='clearbit',
        # )
        return None

    @staticmethod
    def _enrich_via_crunchbase(company_name: str) -> EnrichmentResult | None:
        """
        Enrich via Crunchbase Basic API.

        Requires: CRUNCHBASE_API_KEY in settings.
        Docs: https://data.crunchbase.com/docs/using-the-api
        """
        # import requests
        # from django.conf import settings
        # url = "https://api.crunchbase.com/api/v4/searches/organizations"
        # headers = {"X-cb-user-key": settings.CRUNCHBASE_API_KEY}
        # payload = {"field_ids": ["short_description", "num_employees_enum",
        #            "founded_on", "website_url", "categories"],
        #            "query": [{"type": "predicate", "field_id": "facet_ids",
        #                       "operator_id": "includes", "values": ["company"]},
        #                      {"type": "predicate", "field_id": "name",
        #                       "operator_id": "eq", "values": [company_name]}],
        #            "limit": 1}
        # resp = requests.post(url, json=payload, headers=headers, timeout=10)
        # if resp.status_code != 200 or not resp.json().get('entities'):
        #     return None
        # entity = resp.json()['entities'][0]['properties']
        # return EnrichmentResult(
        #     description=entity.get('short_description'),
        #     employee_count=None,  # parse from enum if needed
        #     industry=entity.get('categories', [{}])[0].get('value'),
        #     founded_year=int(entity['founded_on']['value'][:4]) if entity.get('founded_on') else None,
        #     website=entity.get('website_url'),
        #     source='crunchbase',
        # )
        return None
