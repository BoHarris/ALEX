from __future__ import annotations

from dataclasses import dataclass


GDPR_PERSONAL_DATA = "GDPR_PERSONAL_DATA"
HIPAA_IDENTIFIER = "HIPAA_IDENTIFIER"
COPPA_CHILD_DATA = "COPPA_CHILD_DATA"
SPECIAL_CATEGORY_HEALTH_DATA = "SPECIAL_CATEGORY_HEALTH_DATA"

PII_EMAIL = "PII_EMAIL"
PII_PHONE = "PII_PHONE"
PII_NAME = "PII_NAME"
PII_ADDRESS = "PII_ADDRESS"
PII_IP_ADDRESS = "PII_IP_ADDRESS"
PII_SSN = "PII_SSN"
PII_DATE_OF_BIRTH = "PII_DATE_OF_BIRTH"
PII_SENSITIVE_DATA = "PII_SENSITIVE_DATA"
SENSITIVE_HEALTH_TERM = "SENSITIVE_HEALTH_TERM"
SENSITIVE_VETERAN_STATUS = "SENSITIVE_VETERAN_STATUS"


@dataclass(frozen=True)
class TaxonomyEntry:
    code: str
    display_name: str
    description: str
    policy_categories: tuple[str, ...]


TAXONOMY_ENTRIES: dict[str, TaxonomyEntry] = {
    PII_EMAIL: TaxonomyEntry(
        code=PII_EMAIL,
        display_name="Email Address",
        description="Email addresses and mailbox identifiers.",
        policy_categories=(GDPR_PERSONAL_DATA, HIPAA_IDENTIFIER),
    ),
    PII_PHONE: TaxonomyEntry(
        code=PII_PHONE,
        display_name="Phone Number",
        description="Telephone or mobile contact numbers.",
        policy_categories=(GDPR_PERSONAL_DATA, HIPAA_IDENTIFIER),
    ),
    PII_NAME: TaxonomyEntry(
        code=PII_NAME,
        display_name="Full Name",
        description="Direct personal names or name-like identifiers.",
        policy_categories=(GDPR_PERSONAL_DATA, HIPAA_IDENTIFIER),
    ),
    PII_ADDRESS: TaxonomyEntry(
        code=PII_ADDRESS,
        display_name="Postal Address",
        description="Street, city, postal, or residence data.",
        policy_categories=(GDPR_PERSONAL_DATA, HIPAA_IDENTIFIER),
    ),
    PII_IP_ADDRESS: TaxonomyEntry(
        code=PII_IP_ADDRESS,
        display_name="IP Address",
        description="Network address assigned to a device or session.",
        policy_categories=(GDPR_PERSONAL_DATA,),
    ),
    PII_SSN: TaxonomyEntry(
        code=PII_SSN,
        display_name="Social Security Number",
        description="Government-issued national identifier numbers.",
        policy_categories=(GDPR_PERSONAL_DATA, HIPAA_IDENTIFIER),
    ),
    PII_DATE_OF_BIRTH: TaxonomyEntry(
        code=PII_DATE_OF_BIRTH,
        display_name="Date of Birth",
        description="Birth date or age-linked identity data.",
        policy_categories=(GDPR_PERSONAL_DATA, HIPAA_IDENTIFIER, COPPA_CHILD_DATA),
    ),
    PII_SENSITIVE_DATA: TaxonomyEntry(
        code=PII_SENSITIVE_DATA,
        display_name="Sensitive Data Pattern",
        description="A detected sensitive-data pattern without a more specific taxonomy match.",
        policy_categories=(GDPR_PERSONAL_DATA,),
    ),
    SENSITIVE_HEALTH_TERM: TaxonomyEntry(
        code=SENSITIVE_HEALTH_TERM,
        display_name="Health Condition",
        description="Health-related terminology that may indicate regulated health information.",
        policy_categories=(GDPR_PERSONAL_DATA, SPECIAL_CATEGORY_HEALTH_DATA),
    ),
    SENSITIVE_VETERAN_STATUS: TaxonomyEntry(
        code=SENSITIVE_VETERAN_STATUS,
        display_name="Veteran Status",
        description="Military or veteran status references.",
        policy_categories=(GDPR_PERSONAL_DATA,),
    ),
}


PRESIDIO_TO_TAXONOMY: dict[str, str] = {
    "EMAIL_ADDRESS": PII_EMAIL,
    "PHONE_NUMBER": PII_PHONE,
    "PERSON": PII_NAME,
    "DATE_TIME": PII_DATE_OF_BIRTH,
    "US_SSN": PII_SSN,
    "IP_ADDRESS": PII_IP_ADDRESS,
    "LOCATION": PII_ADDRESS,
}


LEGACY_LABEL_TO_TAXONOMY: dict[str, str] = {
    "Email Address": PII_EMAIL,
    "Phone Number": PII_PHONE,
    "Full Name": PII_NAME,
    "Date of Birth / Date": PII_DATE_OF_BIRTH,
    "Social Security Number": PII_SSN,
    "IP Address": PII_IP_ADDRESS,
    "Location": PII_ADDRESS,
    "Health Term": SENSITIVE_HEALTH_TERM,
    "Veteran Status": SENSITIVE_VETERAN_STATUS,
    "Sensitive Data Pattern": PII_SENSITIVE_DATA,
}


POLICY_DISPLAY_NAMES: dict[str, str] = {
    GDPR_PERSONAL_DATA: "GDPR Personal Data",
    HIPAA_IDENTIFIER: "HIPAA Identifier",
    COPPA_CHILD_DATA: "COPPA Child Data",
    SPECIAL_CATEGORY_HEALTH_DATA: "Special Category Health Data",
}


def get_taxonomy_entry(code: str | None) -> TaxonomyEntry:
    normalized = str(code or "").strip().upper()
    if normalized in TAXONOMY_ENTRIES:
        return TAXONOMY_ENTRIES[normalized]
    return TAXONOMY_ENTRIES[PII_SENSITIVE_DATA]


def map_presidio_entity_to_taxonomy(entity_type: str | None) -> str:
    normalized = str(entity_type or "").strip().upper()
    return PRESIDIO_TO_TAXONOMY.get(normalized, PII_SENSITIVE_DATA)


def map_legacy_label_to_taxonomy(label: str | None) -> str:
    cleaned = str(label or "").strip()
    if not cleaned:
        return PII_SENSITIVE_DATA
    if cleaned in TAXONOMY_ENTRIES:
        return cleaned
    return LEGACY_LABEL_TO_TAXONOMY.get(cleaned, PII_SENSITIVE_DATA)


def get_policy_categories(code: str | None) -> list[str]:
    return list(get_taxonomy_entry(code).policy_categories)


def get_display_name(code: str | None) -> str:
    return get_taxonomy_entry(code).display_name


def get_policy_display_names(codes: list[str] | tuple[str, ...]) -> list[str]:
    return [POLICY_DISPLAY_NAMES.get(code, code.replace("_", " ").title()) for code in codes]


def build_redaction_placeholder(code: str | None, policy_category: str | None = None) -> str:
    normalized_code = get_taxonomy_entry(code).code
    if policy_category:
        policy_suffix = str(policy_category).strip().upper()
        return f"[REDACTED_{normalized_code}_{policy_suffix}]"
    return f"[REDACTED_{normalized_code}]"

