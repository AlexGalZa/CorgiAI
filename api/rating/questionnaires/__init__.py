from .cgl import CGLQuestionnaire
from .commercial_auto import CommercialAutoQuestionnaire
from .crime import CrimeQuestionnaire
from .kidnap_ransom import KidnapRansomQuestionnaire
from .med_malpractice import MedMalpracticeQuestionnaire
from .cyber import CyberQuestionnaire
from .do import DOQuestionnaire
from .epl import EPLQuestionnaire
from .fiduciary import FiduciaryQuestionnaire
from .hnoa import HNOAQuestionnaire
from .media import MediaQuestionnaire
from .tech_eo import TechEOQuestionnaire

QUESTIONNAIRE_MODELS = {
    "commercial-general-liability": CGLQuestionnaire,
    "custom-commercial-auto": CommercialAutoQuestionnaire,
    "custom-crime": CrimeQuestionnaire,
    "custom-kidnap-ransom": KidnapRansomQuestionnaire,
    "custom-med-malpractice": MedMalpracticeQuestionnaire,
    "cyber-liability": CyberQuestionnaire,
    "directors-and-officers": DOQuestionnaire,
    "employment-practices-liability": EPLQuestionnaire,
    "fiduciary-liability": FiduciaryQuestionnaire,
    "hired-and-non-owned-auto": HNOAQuestionnaire,
    "media-liability": MediaQuestionnaire,
    "technology-errors-and-omissions": TechEOQuestionnaire,
}


def get_questionnaire_model(coverage_key: str):
    return QUESTIONNAIRE_MODELS.get(coverage_key)


def validate_questionnaire(coverage_key: str, data: dict):
    model_class = get_questionnaire_model(coverage_key)
    if not model_class:
        raise ValueError(f"Unknown coverage: {coverage_key}")
    return model_class(**data)
