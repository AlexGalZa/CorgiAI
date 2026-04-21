from .cgl import DEFINITION as CGL
from .cyber import DEFINITION as CYBER
from .do import DEFINITION as DO
from .epl import DEFINITION as EPL
from .fiduciary import DEFINITION as FIDUCIARY
from .hnoa import DEFINITION as HNOA
from .media import DEFINITION as MEDIA
from .tech_eo import DEFINITION as TECH_EO

DEFINITIONS = {
    "commercial-general-liability": CGL,
    "cyber-liability": CYBER,
    "directors-and-officers": DO,
    "employment-practices-liability": EPL,
    "fiduciary-liability": FIDUCIARY,
    "hired-and-non-owned-auto": HNOA,
    "media-liability": MEDIA,
    "technology-errors-and-omissions": TECH_EO,
}

COVERAGE_KEYS = list(DEFINITIONS.keys())


def get_definition(coverage_key: str):
    return DEFINITIONS.get(coverage_key)
