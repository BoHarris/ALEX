import os
import smtplib
from email.message import EmailMessage
from fastapi import BackgroundTasks
from dotenv import load_dotenv
from pathlib import Path

#load .env
env_path = Path(__file__).parent.parent / "frontend" / ".env"
load_dotenv(env_path)
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM")
FRONTEND_URL = os.getenv("FRONTEND_URL")

def send_verification_email(background_tasks: BackgroundTasks, to_email:str, token:str):
    verify_link = f"{FRONTEND_URL}/verify-email?token={token}"
    subject = "Verify your ALEX.ai account"
    body = ("Welcome to ALEX.ai!\n\n"
            "Please click to verify your email:\n\n"
            f"{verify_link}\n\n"
            "This link expires in 24 hours")
    
    def _send():
        msg = EmailMessage()
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.connect(SMTP_HOST, SMTP_PORT)
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        
    background_tasks.add_task(_send)
        