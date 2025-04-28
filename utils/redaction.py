import re
import pandas as pd

PII_PATTERNS = {
    "email": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
    "phone": r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
    "ssn": r'\b\d{3}-?\d{2}-\d{4}\b',
    "ip": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    "zip": r'\b\d{5}(?:-\d{4})?\b',
    "dob": r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
    "city": r'\b(?:new york|los angeles|miami|chicago|houston|dallas|atlanta)\b',
    "full_name": r'\b(?:[A-Z][a-z]+\s[A-Z][a-z]+)\b'  # Example: "John Doe"
}

# Expandable known terms
GENDER_TERMS = {
    "male", "female", "nonbinary", "trans", "woman", "man", "mtf", "ftm", "genderqueer",
    "transgender", "cisgender", "femme", "masculine", "feminine", "neutrois", "intersex", "agender"
}

KNOWN_NAMES = {"alice", "bob", "charlie", "john", "jane"}

CITY_NAMES = {"new york", "los angeles", "miami", "chicago", "jacksonville"}

STREET_SUFFIXES = {
    "st", "street", "ave", "avenue", "road", "rd", "blvd", "ln", "lane",
    "dr", "drive", "ct", "court", "pl", "place", "ter", "terrace", "pkwy", "parkway"
}

def contains_any_term(value: str, term_set: set) -> bool:
    value = value.strip().lower()
    return any(re.search(rf'\b{re.escape(term)}\b', value) for term in term_set)

def scan_and_redact_column_with_count(series: pd.Series):
    redacted = series.astype(str).apply(lambda x: x if isinstance(x, str) else str(x))
    redacted_count = 0

    def redact_value(val: str) -> str:
        nonlocal redacted_count
        if pd.isna(val) or not isinstance(val, str):
            return val
        lower_val = val.lower()

        for label, regex in PII_PATTERNS.items():
            if re.search(regex, val, flags=re.IGNORECASE):
                return f"[REDACTED_{label.upper()}]"

        if contains_any_term(lower_val, GENDER_TERMS):
            return "[REDACTED_GENDER]"

        if contains_any_term(lower_val, KNOWN_NAMES):
            return "[REDACTED_NAME]"

        if contains_any_term(lower_val, CITY_NAMES):
            return "[REDACTED_CITY]"

        if contains_any_term(lower_val, STREET_SUFFIXES):
            return "[REDACTED_ADDRESS]"

        return val
    redacted_series = redacted.apply(redact_value)
    total_values = len(series)

    return redacted_series, redacted_count, total_values, redacted_count / total_values if total_values > 0 else 0.0
