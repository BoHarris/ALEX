from fastapi import Request, HTTPException, Depends
from utils.auth_utils import decode_token
from utils.tier_limiter import check_scan_allowed

async def enforce_tier_limit(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    payload = decode_token(token)
    user_id = payload.get("sub")
    tier = payload.get("tier", "free")
    
    allowed = check_scan_allowed(user_id, tier)
    if not allowed:
        raise HTTPException(status_code=403, detail="Daily scan limit reached")
    return{"user_id": user_id, "tier": tier}