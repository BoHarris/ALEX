from typing import List, Dict

PURPOSE_POLICY: Dict[str, Dict[str,List[str]]]={
    "analytics":{
        "allowed_pii":[]
    },
    "fraud_detection":{
        "allowed_pii":["IP_ADDRESS", "EMAIL_ADDRESS"]
    },
    "marketing":{
        "allowed_PII":["EMAIL_ADDRESS"]
    },
    "internal_audit":{
        "allowed_pii":["EMAIL_ADDRESS", "IP_ADDRESS", "DATE_TIME", "ORGANIZATION"]
    },
    "research":{
        "allowed_Pii": ["DATE_TIME"]
    }
}

def create_purpose_policy(purpose: str):
    purpose = purpose.strip().lower()
    if purpose not in PURPOSE_POLICY:
        PURPOSE_POLICY[purpose] = {"allowed_pii": []}
        
def set_purpose_policy(purpose: str, allowed_pii: List[str]):
    purpose = purpose.strip().lower()
    PURPOSE_POLICY[purpose] = {"allowed_pii": allowed_pii}
    
def get_allowed_entities_for_purpose(purpose: str) -> List[str]:
    purpose = purpose.strip().lower()
    return PURPOSE_POLICY.get(purpose, {}).get("allowed_pii", [])