from typing import Literal
from pydantic import BaseModel


ServiceCriticality = Literal["not-critical", "moderately-critical", "highly-critical"]
IndustryHazard = Literal["healthcare", "fintech", "govtech", "industrial", "none"]
AICoverageOption = Literal[
    "algorithmic-bias-liability",
    "ai-intellectual-property-liability",
    "regulatory-investigation-defense-costs",
    "hallucination-defamation-liability",
    "training-data-misuse-liability",
    "data-poisoning-adversarial-attack",
    "service-interruption-liability",
    "bodily-injury-property-damage-autonomous-ai",
    "deepfake-synthetic-media-liability",
    "civil-fines-penalties",
]


class TechEOQuestionnaire(BaseModel):
    services_description: str
    service_criticality: ServiceCriticality
    industry_hazards: list[IndustryHazard]
    has_liability_protections: bool
    has_quality_assurance: bool
    has_prior_incidents: bool
    incident_details: str | None = None
    uses_ai: bool
    wants_ai_coverage: bool | None = None
    ai_coverage_options: list[AICoverageOption] | None = None
