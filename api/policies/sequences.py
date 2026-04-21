from datetime import date

from django.db import models
from django.db.models import F

COVERAGE_CODES = {
    "commercial-general-liability": "CG",
    "cyber-liability": "CY",
    "directors-and-officers": "DO",
    "employment-practices-liability": "EP",
    "fiduciary-liability": "FI",
    "hired-and-non-owned-auto": "HA",
    "media-liability": "ML",
    "technology-errors-and-omissions": "TE",
    "representations-warranties": "RW",
    "custom-cgl": "BCG",
    "custom-do": "BDO",
    "custom-eo": "BEO",
    "custom-tech-eo": "BTE",
    "custom-cyber": "BCY",
    "custom-epli": "BEP",
    "custom-workers-comp": "BWC",
    "custom-bop": "BBP",
    "custom-umbrella": "BUM",
    "custom-excess-liability": "BEL",
    "custom-hnoa": "BHA",
    "custom-commercial-auto": "BCA",
    "custom-crime": "BCR",
    "custom-kidnap-ransom": "BKR",
    "custom-med-malpractice": "BMM",
    "custom-property": "BPR",
    "custom-surety": "BSU",
    "custom-fiduciary": "BFI",
    "custom-media": "BML",
    "custom-other": "BOT",
}


class PolicySequence(models.Model):
    lob_code = models.CharField(max_length=3)
    state = models.CharField(max_length=2)
    year = models.IntegerField()
    last_sequence = models.IntegerField(default=0)

    class Meta:
        db_table = "policy_sequences"
        unique_together = ["lob_code", "state", "year"]

    def __str__(self):
        return f"{self.lob_code}-{self.state}-{self.year}: {self.last_sequence}"


class COISequence(models.Model):
    state = models.CharField(max_length=2)
    year = models.IntegerField()
    last_sequence = models.IntegerField(default=0)

    class Meta:
        db_table = "coi_sequences"
        unique_together = ["state", "year"]

    def __str__(self):
        return f"COI-{self.state}-{self.year}: {self.last_sequence}"


def generate_policy_number(
    coverage_type: str, state: str, effective_date: date, term: int = 1
) -> str:
    lob_code = COVERAGE_CODES.get(coverage_type)
    if not lob_code:
        raise ValueError(f"Unknown coverage type: {coverage_type}")

    year = effective_date.year % 100

    seq, created = PolicySequence.objects.get_or_create(
        lob_code=lob_code, state=state, year=year, defaults={"last_sequence": 0}
    )

    PolicySequence.objects.filter(lob_code=lob_code, state=state, year=year).update(
        last_sequence=F("last_sequence") + 1
    )

    seq.refresh_from_db()

    return f"{lob_code}-{state}-{year:02d}-{seq.last_sequence:06d}-{term:02d}"


def generate_coi_number(state: str, effective_date: date) -> str:
    year = effective_date.year % 100

    seq, created = COISequence.objects.get_or_create(
        state=state, year=year, defaults={"last_sequence": 0}
    )

    COISequence.objects.filter(state=state, year=year).update(
        last_sequence=F("last_sequence") + 1
    )

    seq.refresh_from_db()

    return f"COI-{state}-{year:02d}-{seq.last_sequence:06d}"
