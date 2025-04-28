import smtplib
from email.message import EmailMessage
from fastapi import BackgroundTasks

def send_verification_email(background_tasks: BackgroundTasks, to_email:str, token:str):
    verify_link = "f{FRONTEND_URL}/verify-email?token={token}"
    subject = "Verify your ALEX.ai account"
    body = f"Welsome to ALEX.ai!\n\nPlease click to verify your email:/n/n{verify-link}\n\nThis link expires in 24 hours"
    
    def _send():
        msg = EmailMessage()
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg ["Subject"] = subject
        msg.set_content(body)
        
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)
        
    background_tasks.add_task(_send)
        