import re
import pandas as pd
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from utils.youth_redaction import is_dob_column, calculate_age,get_age_based_redaction_labels
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

def contains_sensitive_term(value: str, terms: set) -> str:
    lower = value.lower()
    for term in terms:
        if re.search(rf'\b{re.escape(term)}\b', lower):
            return term
    return None

def scan_and_redact_column_with_count(series: pd.Series, column_name: str):
    redacted_count = 0
    total_values = len(series)

    def redact_value(val: str) -> str:
        nonlocal redacted_count
        if pd.isna(val):
            return val
        val_str = str(val)
        
        results = analyzer.analyze(text=val_str, language='en')
        if results:
            redacted_count += 1
            val_str = anonymizer.anonymize(text=val_str, analyzer_results=results).text

        # Custom redactions
        if contains_sensitive_term(val_str, HEALTH_TERMS):
            redacted_count += 1
            return "[REDACTED_HEALTH]"

        if contains_sensitive_term(val_str, VETERAN_TERMS):
            redacted_count += 1
            return "[REDACTED_VETERAN]"
        # Below this line Alex is where I am asking for the val_str or should I use col
        if is_dob_column(column_name):
            age = calculate_age(val_str)
            if age is not None:
                labels = get_age_based_redaction_labels(age)
                if labels:
                    redacted_count += 1
                    return "[" + ", ".join(labels) + "]"
        return val_str
    redacted_series = series.apply(redact_value)
    risk_score = redacted_count / total_values if total_values > 0 else 0.0
    
    return redacted_series, redacted_count, total_values, round(risk_score,2)
