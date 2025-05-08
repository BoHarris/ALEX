from collections import defaultdict
from datetime import datetime

scan_log = defaultdict(lambda: {"count": 0, "last_reset": datetime.now()})

def check_scan_allowed(user_id: str, tier: str) -> bool:
    if tier.lower() in ["pro", "business"]:
        return True
    
    log = scan_log[user_id]
    now = datetime.timezone.utc()
    
    if (now - log["last_reset"]).days >= 1:
        log["count"] = 0
        log["last_reset"] = now
        
    if log["count"] < 1:
        log["count"] += 1
        return True
    return False