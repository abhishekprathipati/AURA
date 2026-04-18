from app import app
from aura.utils.parent_verification import send_parent_verification_email

with app.app_context():
    mail_ext = app.extensions.get('mail')
    email_sent = send_parent_verification_email(
        mail_ext,
        "Test Student",
        "student@college.edu",
        "abhishekprathipati07@gmail.com",
        "http://localhost/verify",
        "Test Parent"
    )
    print("Email Sent Status:", email_sent)
