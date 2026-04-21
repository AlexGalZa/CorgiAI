from dataclasses import dataclass, field
from typing import Optional
from datetime import date

from common.utils import format_currency


DATE_FORMAT = "%m/%d/%Y"


def format_currency_with_symbol(amount: int | float) -> str:
    return f"${format_currency(amount)}"


@dataclass
class CGLLimitsInput:
    per_occurrence: int
    aggregate: int
    retention: int
    has_products_completed_operations: bool = False


@dataclass
class HNOALimitsInput:
    per_occurrence: int
    aggregate: int
    retention: int


@dataclass
class TechCoverageInput:
    name: str
    policy_number: str
    per_occurrence: int
    aggregate: int
    retention: int
    form_code: str = ""


@dataclass
class TechFormEntry:
    name: str
    code: str


@dataclass
class CGLMasterFormInput:
    name_insured: str
    policy_start_date: date
    policy_end_date: date
    insured_address: str
    retroactive_date: date
    cgl_policy_number: str
    cgl: CGLLimitsInput
    hnoa: Optional[HNOALimitsInput] = None

    def to_form_fields(self) -> dict:
        fields = {
            "name_insured": self.name_insured,
            "policy_start_date": self.policy_start_date.strftime(DATE_FORMAT),
            "policy_end_date": self.policy_end_date.strftime(DATE_FORMAT),
            "insured_address": self.insured_address,
            "retroactive_date": self.retroactive_date.strftime(DATE_FORMAT),
            "cgl_title": "Commercial General Liability",
            "cgl_policy_number": f"Policy #: {self.cgl_policy_number}",
            "cgl_description": "",
            "cgl_per_ocurrence": f"Each Claim {format_currency_with_symbol(self.cgl.per_occurrence)}",
            "cgl_aggregate_limit": f"Aggregate {format_currency_with_symbol(self.cgl.aggregate)}",
            "cgl_retention_limit": f"Retention {format_currency_with_symbol(self.cgl.retention)}",
            "cgl_content_a1": "Products-Completed Operations Limit",
            "cgl_content_a2": f"{format_currency_with_symbol(self.cgl.aggregate)} aggregate"
            if self.cgl.has_products_completed_operations
            else "$0 aggregate",
            "cgl_content_b1": "Personal and Advertising Injury Limit",
            "cgl_content_b2": "$0 aggregate",
            "cgl_content_c1": "Damage To Premises Rented To You Limit",
            "cgl_content_c2": "$100,000 aggregate",
            "cgl_content_d1": "Medical Expenses Limit",
            "cgl_content_d2": "$5,000 aggregate",
            "cgl_content_e1": "",
            "cgl_content_e2": "",
            "form_name_a1": "Master Declarations Page (CGL)",
            "form_code_a2": "CORG-CGL-0001",
            "form_name_b1": "Commercial General Liability Insurance Policy (Occurrence)",
            "form_name_b2": "CORG-CGL-0100",
            "form_name_c1": "",
            "form_name_c2": "",
        }

        if self.hnoa:
            fields.update(
                {
                    "hnoa_title": "Hired and Non-Owned Auto Liability",
                    "hnoa_description": "Endorsement",
                    "hnoa_policy_number": f"Policy #: {self.cgl_policy_number}",
                    "hnoa_per_ocurrence": f"Each Claim {format_currency_with_symbol(self.hnoa.per_occurrence)}",
                    "hnoa_aggregate_limit": f"Aggregate {format_currency_with_symbol(self.hnoa.aggregate)}",
                    "hnoa_retention_limit": f"Retention {format_currency_with_symbol(self.hnoa.retention)}",
                    "form_name_c1": "Hired and Non-Owned Auto Liability Endorsement",
                    "form_name_c2": "CORG-CGL-0101",
                }
            )

        return fields


@dataclass
class TechMasterFormInput:
    name_insured: str
    policy_start_date: date
    policy_end_date: date
    insured_address: str
    retroactive_date: date
    coverages: list[TechCoverageInput] = field(default_factory=list)
    form_entries: list[TechFormEntry] = field(default_factory=list)

    def to_form_fields(self) -> dict:
        fields = {
            "name_insured": self.name_insured,
            "policy_start_date": self.policy_start_date.strftime(DATE_FORMAT),
            "policy_end_date": self.policy_end_date.strftime(DATE_FORMAT),
            "insured_address": self.insured_address,
            "policy_retroactive_date": self.retroactive_date.strftime(DATE_FORMAT),
        }

        for i, coverage in enumerate(self.coverages[:6], start=1):
            fields[f"coverage_{i}"] = coverage.name
            fields[f"coverage_{i}_policy_number"] = (
                f"Policy #: {coverage.policy_number}"
            )
            fields[f"coverage_{i}_per_ocurrence"] = (
                f"Each Claim {format_currency_with_symbol(coverage.per_occurrence)}"
            )
            fields[f"coverage_{i}_aggregate"] = (
                f"Aggregate {format_currency_with_symbol(coverage.aggregate)}"
            )
            fields[f"coverage_{i}_retention"] = (
                f"Retention {format_currency_with_symbol(coverage.retention)}"
            )

        # Populate form name/code fields (up to 14 entries)
        for i, form_entry in enumerate(self.form_entries[:14], start=1):
            fields[f"form_name_{i}"] = form_entry.name
            fields[f"form_code_{i}"] = form_entry.code

        return fields


@dataclass
class CertificateHolderInput:
    name: str
    address_line1: str = ""
    city_state_zip: str = ""


@dataclass
class COIProducerInput:
    name: str
    address_line1: str
    address_line2: str
    contact_name: str
    phone: str
    email: str


@dataclass
class COIInsurerInput:
    name: str
    naic_code: str


@dataclass
class COIInsuredInput:
    name: str
    address_line1: str
    address_line2: str


@dataclass
class COIGeneralLiabilityInput:
    insurer_letter: str
    policy_number: str
    effective_date: str
    expiration_date: str
    each_occurrence: str
    damage_to_rented: str
    med_exp: str
    general_aggregate: str
    products_comp_op_agg: str


@dataclass
class COIAutoLiabilityInput:
    insurer_letter: str
    policy_number: str
    effective_date: str
    expiration_date: str
    combined_single_limit: str = ""
    bodily_injury_per_person: str = ""
    bodily_injury_per_accident: str = ""
    property_damage_per_accident: str = ""


@dataclass
class COIAdditionalCoverageInput:
    name: str
    policy_number: str
    effective_date: str
    expiration_date: str
    per_claim_limit: str
    aggregate_limit: str


@dataclass
class COIFormInput:
    certificate_date: str
    certificate_number: str
    revision_number: str = "1"
    producer: Optional[COIProducerInput] = None
    insurer: Optional[COIInsurerInput] = None
    insured: Optional[COIInsuredInput] = None
    holder: Optional[CertificateHolderInput] = None
    description: str = ""
    general_liability: Optional[COIGeneralLiabilityInput] = None
    auto_liability: Optional[COIAutoLiabilityInput] = None
    additional_coverages: list[COIAdditionalCoverageInput] = field(default_factory=list)

    def to_form_fields(self) -> dict:
        P = "F[0].P1[0]."

        data = {
            f"{P}Form_CompletionDate_A[0]": self.certificate_date,
            f"{P}CertificateOfInsurance_CertificateNumberIdentifier_A[0]": self.certificate_number,
            f"{P}CertificateOfInsurance_RevisionNumberIdentifier_A[0]": self.revision_number,
        }

        if self.producer:
            data.update(
                {
                    f"{P}Producer_FullName_A[0]": self.producer.name,
                    f"{P}Producer_MailingAddress_LineOne_A[0]": self.producer.address_line1,
                    f"{P}Producer_MailingAddress_LineTwo_A[0]": self.producer.address_line2,
                    f"{P}Producer_ContactPerson_FullName_A[0]": self.producer.contact_name,
                    f"{P}Producer_ContactPerson_PhoneNumber_A[0]": self.producer.phone,
                    f"{P}Producer_ContactPerson_EmailAddress_A[0]": self.producer.email,
                }
            )

        if self.insurer:
            data.update(
                {
                    f"{P}Insurer_FullName_A[0]": self.insurer.name,
                    f"{P}Insurer_NAICCode_A[0]": self.insurer.naic_code,
                }
            )

        if self.insured:
            data.update(
                {
                    f"{P}NamedInsured_FullName_A[0]": self.insured.name,
                    f"{P}NamedInsured_MailingAddress_LineOne_A[0]": self.insured.address_line1,
                    f"{P}NamedInsured_MailingAddress_LineTwo_A[0]": self.insured.address_line2,
                }
            )

        if self.holder:
            holder_address = self.holder.address_line1
            if self.holder.city_state_zip:
                holder_address = f"{holder_address}\n{self.holder.city_state_zip}"
            data.update(
                {
                    "CertificateHolderFullName": self.holder.name,
                    "CertificateHolderAddress": holder_address,
                }
            )

        if self.description:
            data["CertificateDescription"] = self.description

        if self.general_liability:
            gl = self.general_liability
            data.update(
                {
                    f"{P}GeneralLiability_InsurerLetterCode_A[0]": gl.insurer_letter,
                    f"{P}GeneralLiability_CoverageIndicator_A[0]": "Yes",
                    f"{P}GeneralLiability_OccurrenceIndicator_A[0]": "Yes",
                    f"{P}GeneralLiability_GeneralAggregate_LimitAppliesPerPolicyIndicator_A[0]": "Yes",
                    f"{P}Policy_GeneralLiability_PolicyNumberIdentifier_A[0]": gl.policy_number,
                    f"{P}Policy_GeneralLiability_EffectiveDate_A[0]": gl.effective_date,
                    f"{P}Policy_GeneralLiability_ExpirationDate_A[0]": gl.expiration_date,
                    f"{P}GeneralLiability_EachOccurrence_LimitAmount_A[0]": gl.each_occurrence,
                    f"{P}GeneralLiability_FireDamageRentedPremises_EachOccurrenceLimitAmount_A[0]": gl.damage_to_rented,
                    f"{P}GeneralLiability_MedicalExpense_EachPersonLimitAmount_A[0]": gl.med_exp,
                    f"{P}GeneralLiability_GeneralAggregate_LimitAmount_A[0]": gl.general_aggregate,
                    f"{P}GeneralLiability_ProductsAndCompletedOperations_AggregateLimitAmount_A[0]": gl.products_comp_op_agg,
                }
            )

        if self.auto_liability:
            auto = self.auto_liability
            data.update(
                {
                    f"{P}Vehicle_InsurerLetterCode_A[0]": auto.insurer_letter,
                    f"{P}Vehicle_HiredAutosIndicator_A[0]": "Yes",
                    f"{P}Vehicle_NonOwnedAutosIndicator_A[0]": "Yes",
                    f"{P}Policy_AutomobileLiability_PolicyNumberIdentifier_A[0]": auto.policy_number,
                    f"{P}Policy_AutomobileLiability_EffectiveDate_A[0]": auto.effective_date,
                    f"{P}Policy_AutomobileLiability_ExpirationDate_A[0]": auto.expiration_date,
                    f"{P}Vehicle_CombinedSingleLimit_EachAccidentAmount_A[0]": auto.combined_single_limit,
                    f"{P}Vehicle_BodilyInjury_PerPersonLimitAmount_A[0]": auto.bodily_injury_per_person,
                    f"{P}Vehicle_BodilyInjury_PerAccidentLimitAmount_A[0]": auto.bodily_injury_per_accident,
                    f"{P}Vehicle_PropertyDamage_PerAccidentLimitAmount_A[0]": auto.property_damage_per_accident,
                }
            )

        if self.additional_coverages:
            letters = []
            names = []
            policy_numbers = []
            eff_dates = []
            exp_dates = []
            limits1 = []
            limits2 = []

            for cov in self.additional_coverages:
                letters.append("A")
                names.append(cov.name)
                policy_numbers.append(cov.policy_number)
                eff_dates.append(cov.effective_date)
                exp_dates.append(cov.expiration_date)
                limits1.append(cov.per_claim_limit)
                limits2.append(cov.aggregate_limit)

            data.update(
                {
                    "Column.Letter": "\n".join(letters),
                    "Column.Coverage": "\n".join(names),
                    "Column.PolicyNumber": "\n".join(policy_numbers),
                    "Column.PolicyEffectiveDate": "\n".join(eff_dates),
                    "Column.PolicyExpirationDate": "\n".join(exp_dates),
                    "Column.Limit1": "\n".join(limits1),
                    "Column.Limit2": "\n".join(limits2),
                }
            )

        return data
