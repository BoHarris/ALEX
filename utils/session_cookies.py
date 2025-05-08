from itsdangerous import TimestampSigner, BadSignature
import os
from dotenv import load_dotenv

load_dotenv()

SIGNER_SECRET = os.getenv("SESSION_SECRET")
signer = TimestampSigner(SIGNER_SECRET)

def create_demo_cookie():
    return signer.sign("demo_used").decode()

def has_used_demo(cookie_value: str):
    try:
        value = signer.unsign(cookie_value, max_age=20*60*60) # this is 1 day 
        return value == b"demo_used"
    except BadSignature:
        return False