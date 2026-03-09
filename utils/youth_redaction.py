from datetime import datetime
from typing import List, Optional

#Global Policy redaction threshold
AGE_POLICY_THRESHOLDS ={
    "HIPPA": 18,
    "COPPA": 13,
    "CCPA": 16,
    "GDPR": 16,
    "PIPEDA": 18,
    "LGDP": 18,
    "PDPA_SG": 13,
    "PDPA_TH": 10,
    "FERPA": 18
}

#Common columns names for DOB Fields
DOB_COLUMN_NAMES ={"dob", "date_of_birth", "birthdate", "birth_date"}

def is_dob_column(column_name: str) -> bool:
    return column_name.strip().lower() in DOB_COLUMN_NAMES

def calculate_age(dob_str: str, date_format: str = "%Y-%m-%d") -> Optional[int]:
    try: 
        dob = datetime.strptime(dob_str, date_format)
        today = datetime.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except Exception:
        return None
    
def get_age_based_redaction_labels(age: int)-> List[str]:
    return[f"REDACTED_{policy}-MINOR" for policy, limit in AGE_POLICY_THRESHOLDS.items() if age <limit]