"""
Email service for sending verification and notification emails.
Supports Resend (recommended) and SMTP.
"""

import secrets
from datetime import UTC, datetime, timedelta

import httpx

from src.core.config import settings


class EmailService:
    """Email service using Resend API."""

    def __init__(self):
        self.api_key = getattr(settings, 'RESEND_API_KEY', None)
        self.from_email = getattr(settings, 'EMAIL_FROM', 'Prometheus <noreply@prometheus.trading>')
        self.frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

    @property
    def is_configured(self) -> bool:
        """Check if email service is configured."""
        return bool(self.api_key)

    async def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: str | None = None
    ) -> bool:
        """
        Send an email using Resend API.

        Args:
            to: Recipient email address
            subject: Email subject
            html: HTML content
            text: Plain text content (optional)

        Returns:
            True if email was sent successfully
        """
        if not self.is_configured:
            print(f"📧 Email service not configured. Would send to {to}: {subject}")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": self.from_email,
                        "to": [to],
                        "subject": subject,
                        "html": html,
                        "text": text or "",
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    print(f"✅ Email sent to {to}: {subject}")
                    return True
                else:
                    print(f"❌ Failed to send email: {response.text}")
                    return False

        except Exception as e:
            print(f"❌ Email error: {e}")
            return False

    async def send_verification_email(self, to: str, token: str, username: str) -> bool:
        """Send email verification link."""
        verify_url = f"{self.frontend_url}/verify-email?token={token}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #09090b; color: #fafafa; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ text-align: center; margin-bottom: 40px; }}
                .logo {{ font-size: 32px; font-weight: bold; color: #F59E0B; letter-spacing: 2px; }}
                .tagline {{ color: #71717a; font-size: 12px; letter-spacing: 3px; margin-top: 8px; }}
                .content {{ background: linear-gradient(180deg, rgba(39, 39, 42, 0.8) 0%, rgba(24, 24, 27, 0.95) 100%); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 16px; padding: 40px; }}
                .greeting {{ font-size: 24px; margin-bottom: 20px; color: #fafafa; }}
                .message {{ color: #a1a1aa; line-height: 1.8; margin-bottom: 30px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%); color: #000; padding: 16px 40px; border-radius: 12px; text-decoration: none; font-weight: 600; font-size: 16px; }}
                .button:hover {{ background: linear-gradient(135deg, #FBBF24 0%, #F59E0B 100%); }}
                .footer {{ text-align: center; margin-top: 40px; color: #52525b; font-size: 12px; }}
                .expire {{ background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 8px; padding: 12px 20px; margin-top: 20px; color: #F59E0B; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🔥 PROMETHEUS</div>
                    <div class="tagline">BRINGER OF FIRE</div>
                </div>
                <div class="content">
                    <div class="greeting">Welcome, {username}!</div>
                    <p class="message">
                        You're one step away from igniting your trading journey.
                        Click the button below to verify your email address and unlock
                        the power of AI-driven trading.
                    </p>
                    <div style="text-align: center;">
                        <a href="{verify_url}" class="button">🔥 Verify My Email</a>
                    </div>
                    <div class="expire">
                        ⏱️ This link expires in 24 hours
                    </div>
                </div>
                <div class="footer">
                    <p>If you didn't create an account, you can safely ignore this email.</p>
                    <p>© 2024 Prometheus Trading Platform</p>
                </div>
            </div>
        </body>
        </html>
        """

        text = f"""
        Welcome to Prometheus, {username}!

        Please verify your email by clicking this link:
        {verify_url}

        This link expires in 24 hours.

        If you didn't create an account, you can safely ignore this email.
        """

        return await self.send_email(
            to=to,
            subject="🔥 Verify your Prometheus account",
            html=html,
            text=text
        )

    async def send_password_reset_email(self, to: str, token: str, username: str) -> bool:
        """Send password reset link."""
        reset_url = f"{self.frontend_url}/reset-password?token={token}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #09090b; color: #fafafa; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ text-align: center; margin-bottom: 40px; }}
                .logo {{ font-size: 32px; font-weight: bold; color: #F59E0B; letter-spacing: 2px; }}
                .tagline {{ color: #71717a; font-size: 12px; letter-spacing: 3px; margin-top: 8px; }}
                .content {{ background: linear-gradient(180deg, rgba(39, 39, 42, 0.8) 0%, rgba(24, 24, 27, 0.95) 100%); border: 1px solid rgba(124, 58, 237, 0.2); border-radius: 16px; padding: 40px; }}
                .greeting {{ font-size: 24px; margin-bottom: 20px; color: #fafafa; }}
                .message {{ color: #a1a1aa; line-height: 1.8; margin-bottom: 30px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%); color: #fff; padding: 16px 40px; border-radius: 12px; text-decoration: none; font-weight: 600; font-size: 16px; }}
                .footer {{ text-align: center; margin-top: 40px; color: #52525b; font-size: 12px; }}
                .warning {{ background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 8px; padding: 12px 20px; margin-top: 20px; color: #EF4444; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🔥 PROMETHEUS</div>
                    <div class="tagline">BRINGER OF FIRE</div>
                </div>
                <div class="content">
                    <div class="greeting">Password Reset Request</div>
                    <p class="message">
                        Hi {username}, we received a request to reset your password.
                        Click the button below to create a new password.
                    </p>
                    <div style="text-align: center;">
                        <a href="{reset_url}" class="button">🔐 Reset Password</a>
                    </div>
                    <div class="warning">
                        ⚠️ This link expires in 1 hour. If you didn't request this, please ignore this email.
                    </div>
                </div>
                <div class="footer">
                    <p>© 2024 Prometheus Trading Platform</p>
                </div>
            </div>
        </body>
        </html>
        """

        text = f"""
        Password Reset Request

        Hi {username},

        Click this link to reset your password:
        {reset_url}

        This link expires in 1 hour.

        If you didn't request this, please ignore this email.
        """

        return await self.send_email(
            to=to,
            subject="🔐 Reset your Prometheus password",
            html=html,
            text=text
        )

    async def send_welcome_email(self, to: str, username: str) -> bool:
        """Send welcome email after verification."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #09090b; color: #fafafa; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ text-align: center; margin-bottom: 40px; }}
                .logo {{ font-size: 32px; font-weight: bold; color: #F59E0B; letter-spacing: 2px; }}
                .content {{ background: linear-gradient(180deg, rgba(39, 39, 42, 0.8) 0%, rgba(24, 24, 27, 0.95) 100%); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 16px; padding: 40px; }}
                .greeting {{ font-size: 28px; margin-bottom: 20px; color: #10B981; }}
                .message {{ color: #a1a1aa; line-height: 1.8; margin-bottom: 30px; }}
                .feature {{ background: rgba(245, 158, 11, 0.05); border-left: 3px solid #F59E0B; padding: 15px 20px; margin: 15px 0; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%); color: #000; padding: 16px 40px; border-radius: 12px; text-decoration: none; font-weight: 600; font-size: 16px; }}
                .footer {{ text-align: center; margin-top: 40px; color: #52525b; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🔥 PROMETHEUS</div>
                </div>
                <div class="content">
                    <div class="greeting">✅ Welcome to the Titans, {username}!</div>
                    <p class="message">
                        Your email has been verified. You now have full access to the Prometheus trading platform.
                    </p>
                    <div class="feature">🤖 <strong>AI Analysis</strong> - 8+ AI models analyzing markets in real-time</div>
                    <div class="feature">📊 <strong>Auto Trading</strong> - Let AI execute trades for you</div>
                    <div class="feature">🔥 <strong>Multi-Broker</strong> - Connect MetaTrader, Alpaca & more</div>
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="{self.frontend_url}/dashboard" class="button">🚀 Go to Dashboard</a>
                    </div>
                </div>
                <div class="footer">
                    <p>© 2024 Prometheus Trading Platform</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self.send_email(
            to=to,
            subject="🎉 Welcome to Prometheus - Account Verified!",
            html=html,
            text=f"Welcome {username}! Your Prometheus account is now verified. Go to {self.frontend_url}/dashboard to start trading."
        )

    async def send_license_email(
        self,
        to: str,
        license_key: str,
        product_name: str,
        expires_at: datetime | None = None,
        order_id: str | None = None,
    ) -> bool:
        """Send a license key to a customer after purchase."""
        expires_text = (
            expires_at.strftime("%Y-%m-%d %H:%M UTC") if expires_at else "No expiration"
        )

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #09090b; color: #fafafa; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 32px; font-weight: bold; color: #F59E0B; letter-spacing: 2px; }}
                .content {{ background: linear-gradient(180deg, rgba(39, 39, 42, 0.8) 0%, rgba(24, 24, 27, 0.95) 100%); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 16px; padding: 32px; }}
                .title {{ font-size: 24px; margin-bottom: 16px; color: #fafafa; }}
                .message {{ color: #a1a1aa; line-height: 1.8; margin-bottom: 24px; }}
                .license {{ background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 12px; padding: 16px; text-align: center; }}
                .license code {{ font-family: monospace; font-size: 20px; color: #F59E0B; letter-spacing: 1px; }}
                .meta {{ color: #71717a; font-size: 13px; margin-top: 14px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%); color: #000; padding: 14px 26px; border-radius: 10px; text-decoration: none; font-weight: 600; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">PROMETHEUS</div>
                </div>
                <div class="content">
                    <div class="title">Your license key is ready</div>
                    <p class="message">
                        Thank you for your purchase of <strong>{product_name}</strong>.
                        Use this key during account registration:
                    </p>
                    <div class="license">
                        <code>{license_key}</code>
                    </div>
                    <p class="meta">Expires: {expires_text}</p>
                    {f'<p class="meta">Order: {order_id}</p>' if order_id else ''}
                    <div style="text-align: center; margin-top: 24px;">
                        <a href="{self.frontend_url}/register" class="button">Go to Registration</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        order_line = f"Order: {order_id}\n" if order_id else ""
        text = (
            f"Your Prometheus license key: {license_key}\n"
            f"Product: {product_name}\n"
            f"Expires: {expires_text}\n"
            f"{order_line}"
            f"Register here: {self.frontend_url}/register"
        )

        return await self.send_email(
            to=to,
            subject="Your Prometheus license key",
            html=html,
            text=text,
        )


def generate_verification_token() -> str:
    """Generate a secure random token for email verification."""
    return secrets.token_urlsafe(32)


def get_token_expiry(hours: int = 24) -> datetime:
    """Get expiry datetime for a token."""
    return datetime.now(UTC) + timedelta(hours=hours)


# Global email service instance
email_service = EmailService()
