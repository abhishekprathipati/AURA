"""
Email template generators for OTP and notifications.
Provides HTML and plain-text versions of email templates.
"""


def get_otp_email_template(otp: str, expiry_minutes: int = 5) -> tuple[str, str, str]:
    """
    Generate OTP email template.

    Returns: (subject: str, html_body: str, text_body: str)
    """
    subject = "Your AURA Parent Portal Login Code"

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
        .otp-box {{ background: white; border: 2px dashed #667eea; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0; }}
        .otp-code {{ font-size: 48px; font-weight: bold; letter-spacing: 8px; color: #667eea; font-family: 'Courier New', monospace; }}
        .info {{ color: #666; font-size: 14px; margin: 20px 0; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 20px 0; border-radius: 4px; color: #856404; }}
        .disclaimer {{ color: #999; font-size: 12px; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 20px; }}
        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 AURA Parent Portal</h1>
            <p>Your One-Time Login Code</p>
        </div>

        <div class="content">
            <p>Hello,</p>

            <p>You requested a login code to access the AURA Parent Portal. Use the code below to verify your phone number and access your ward's wellness information.</p>

            <div class="otp-box">
                <p style="margin: 0 0 10px 0; color: #999; font-size: 12px;">Your Login Code</p>
                <div class="otp-code">{otp}</div>
            </div>

            <div class="info">
                <strong>⏱️ Code expires in:</strong> {expiry_minutes} minutes
            </div>

            <div class="warning">
                <strong>🔒 Security Alert:</strong> Never share this code with anyone. AURA staff will never ask for your login code.
            </div>

            <p style="color: #666; font-size: 14px; margin-top: 20px;">
                If you didn't request this code, please ignore this email. Your account remains secure.
            </p>

            <div class="disclaimer">
                <p style="margin: 0;">This is an automated message. Please do not reply to this email.</p>
                <p style="margin: 5px 0 0 0;">
                    <strong>AURA Student Wellness Monitoring System</strong>
                </p>
            </div>
        </div>

        <div class="footer">
            <p>&copy; 2026 AURA. All rights reserved. | <a href="#" style="color: #667eea; text-decoration: none;">Privacy Policy</a></p>
        </div>
    </div>
</body>
</html>
"""

    text_body = f"""
AURA Parent Portal - Your Login Code
=====================================

Hello,

You requested a login code to access the AURA Parent Portal. Use the code below to verify your phone number and access your ward's wellness information.

Your Login Code: {otp}

Code expires in: {expiry_minutes} minutes

SECURITY ALERT:
Never share this code with anyone. AURA staff will never ask for your login code.

If you didn't request this code, please ignore this email. Your account remains secure.

---
This is an automated message. Please do not reply to this email.
AURA Student Wellness Monitoring System
© 2026 AURA. All rights reserved.
"""

    return subject, html_body, text_body
