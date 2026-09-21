import logging
import smtplib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from config import settings

logger = logging.getLogger("email_service")

class EmailService:
    @staticmethod
    def construct_reset_url(reset_token: str) -> str:
        """Construct the password reset URL using configured FRONTEND_URL."""
        base_url = settings.FRONTEND_URL.rstrip("/")
        encoded_token = urllib.parse.quote(reset_token)
        return f"{base_url}/reset-password?token={encoded_token}"

    @classmethod
    def send_password_reset_email(
        cls,
        to_email: str,
        reset_token: str,
        user_name: Optional[str] = None
    ) -> bool:
        """
        Deliver a password reset link to the recipient email address.
        Uses standard SMTP when configured; gracefully falls back in local development.
        Logs never contain raw tokens, passwords, or full reset URLs.
        """
        reset_url = cls.construct_reset_url(reset_token)
        expiration_minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        name_greeting = f"Hello {user_name}," if user_name else "Hello,"

        subject = "Reset Your FinRisk AI Password"

        # Plain-text version
        text_body = f"""{name_greeting}

We received a request to reset your password for your FinRisk AI account.

To choose a new password, open the following link in your browser:
{reset_url}

This link will expire in {expiration_minutes} minutes.

If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.

Best regards,
The FinRisk AI Team
"""

        # HTML version
        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #020617; color: #e2e8f0; margin: 0; padding: 24px; }}
    .container {{ max-width: 540px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 32px; }}
    .brand {{ color: #10b981; font-weight: 700; font-size: 20px; letter-spacing: -0.5px; margin-bottom: 24px; }}
    h1 {{ font-size: 22px; color: #ffffff; margin-top: 0; }}
    p {{ font-size: 15px; line-height: 1.6; color: #94a3b8; }}
    .btn {{ display: inline-block; padding: 12px 28px; background-color: #10b981; color: #020617 !important; font-weight: 700; text-decoration: none; border-radius: 10px; margin: 20px 0; font-size: 15px; }}
    .link-fallback {{ font-size: 13px; color: #64748b; word-break: break-all; margin-top: 16px; }}
    .notice {{ font-size: 13px; color: #64748b; border-top: 1px solid #1e293b; padding-top: 20px; margin-top: 28px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="brand">FinRisk AI</div>
    <h1>Password Reset Request</h1>
    <p>{name_greeting}</p>
    <p>We received a request to reset your password for your FinRisk AI account. Click the button below to set a new password:</p>
    <p><a href="{reset_url}" class="btn" target="_blank">Reset Password</a></p>
    <p class="link-fallback">If the button doesn't work, copy and paste this link into your browser:<br><a href="{reset_url}" style="color: #10b981;">{reset_url}</a></p>
    <div class="notice">
      <p><strong>Note:</strong> This link is valid for <strong>{expiration_minutes} minutes</strong> and can only be used once.</p>
      <p>If you did not request this password reset, you can safely ignore this email. Your password will remain unchanged.</p>
    </div>
  </div>
</body>
</html>"""

        # If SMTP is configured, attempt sending real email
        if settings.SMTP_HOST:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = settings.SMTP_FROM_EMAIL
                msg["To"] = to_email

                part1 = MIMEText(text_body, "plain", "utf-8")
                part2 = MIMEText(html_body, "html", "utf-8")
                msg.attach(part1)
                msg.attach(part2)

                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                try:
                    if settings.SMTP_USE_TLS:
                        server.starttls()
                    if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.send_message(msg)
                    logger.info("Password reset email sent successfully to %s", to_email)
                    return True
                finally:
                    server.quit()
            except Exception as e:
                # Log sanitized exception type without exposing credentials or payload
                logger.error("SMTP delivery failed for recipient (%s): %s", type(e).__name__, str(e)[:100])
                return False
        else:
            # Safe development / test mode fallback
            logger.info("SMTP_HOST not set. Safe local mode: password reset requested for %s. (No external email sent)", to_email)
            return True

# Reusable module instance
email_service = EmailService()
