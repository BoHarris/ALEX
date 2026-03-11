import re
import pandas as pd
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from utils.pii_taxonomy import (
    PII_DATE_OF_BIRTH,
    PII_PHONE,
    SENSITIVE_HEALTH_TERM,
    SENSITIVE_VETERAN_STATUS,
    build_redaction_placeholder,
    get_display_name,
    map_presidio_entity_to_taxonomy,
)
from utils.youth_redaction import is_dob_column, calculate_age, get_age_based_redaction_labels
# Initialize Presidio engines
analyzer = AnalyzerEngine()
anonymizer  = AnonymizerEngine()

HEALTH_TERMS = {
    "cancer", "diabetes", "depression", "anxiety", "hiv", "autism", "asthma",
    "covid", "bipolar", "schizophrenia", "hypertension", "ptsd", "adhd"
}

VETERAN_TERMS = {
    "veteran", "military", "army", "navy", "air force", "marine", "service member"
}

#add 7 digit phone number redaction
PHONE_7_RE = re.compile(r"\b\d{3}-\d{4}\b")
PHONE_HINT_RE = re.compile(R"\b(phone|tel|telephone|mobile|cell|call)\b", re.I)

def contains_sensitive_term(value: str, terms: set) -> str:
    lower = value.lower()
    for term in terms:
        if re.search(rf'\b{re.escape(term)}\b', lower):
            return term
    return None


def _normalize_entity_label(entity_type: str | None) -> str:
    return get_display_name(map_presidio_entity_to_taxonomy(entity_type))


def scan_and_redact_column_with_details(series: pd.Series, column_name: str = "", aggressive: bool =False):
    redacted_count = 0
    total_values = len(series)
    type_counts: dict[str, int] = {}

    def add_type_count(label: str) -> None:
        type_counts[label] = type_counts.get(label, 0) + 1

    def redact_value(val: str) -> str:
        nonlocal redacted_count
        if pd.isna(val):
            return val
        val_str = str(val)
        
        results = analyzer.analyze(text=val_str, language='en')
        if results:
            redacted_count += 1
            seen_taxonomy_codes = {map_presidio_entity_to_taxonomy(result.entity_type) for result in results}
            primary_taxonomy = sorted(seen_taxonomy_codes)[0]
            for taxonomy_code in seen_taxonomy_codes:
                add_type_count(taxonomy_code)
            operator_map = {
                result.entity_type: OperatorConfig(
                    "replace",
                    {"new_value": build_redaction_placeholder(map_presidio_entity_to_taxonomy(result.entity_type))},
                )
                for result in results
                if result.entity_type
            }
            if not operator_map:
                operator_map = {
                    "DEFAULT": OperatorConfig("replace", {"new_value": build_redaction_placeholder(primary_taxonomy)})
                }
            val_str = anonymizer.anonymize(text=val_str, analyzer_results=results, operators=operator_map).text

        # Custom redactions
        if contains_sensitive_term(val_str, HEALTH_TERMS):
            redacted_count += 1
            add_type_count(SENSITIVE_HEALTH_TERM)
            return build_redaction_placeholder(SENSITIVE_HEALTH_TERM)

        if contains_sensitive_term(val_str, VETERAN_TERMS):
            redacted_count += 1
            add_type_count(SENSITIVE_VETERAN_STATUS)
            return build_redaction_placeholder(SENSITIVE_VETERAN_STATUS)
        
        
        if PHONE_7_RE.search(val_str):
            has_hint_in_text = bool(PHONE_HINT_RE.search(val_str))
            col_l = (column_name or "").lower()
            has_hint_in_col = ("phone" in col_l) or ("tel" in col_l)

            if aggressive or has_hint_in_text or has_hint_in_col:
                val_str = PHONE_7_RE.sub(build_redaction_placeholder(PII_PHONE), val_str)
                redacted_count += 1
                add_type_count(PII_PHONE)
        
        # DOB / youth policy logic
        if is_dob_column(column_name):
            age = calculate_age(val_str)
            if age is not None:
                labels = get_age_based_redaction_labels(age)
                if labels:
                    redacted_count += 1
                    add_type_count(PII_DATE_OF_BIRTH)
                    return build_redaction_placeholder(PII_DATE_OF_BIRTH, labels[0].replace("REDACTED_", ""))
        return val_str
    
    redacted_series = series.apply(redact_value)
    risk_score = redacted_count / total_values if total_values > 0 else 0.0
    return redacted_series, redacted_count, total_values, round(risk_score,2), type_counts


def scan_and_redact_column_with_count(series: pd.Series, column_name: str = "", aggressive: bool =False):
    redacted_series, redacted_count, total_values, risk_score, _ = scan_and_redact_column_with_details(
        series,
        column_name,
        aggressive,
    )
    return redacted_series, redacted_count, total_values, risk_score
