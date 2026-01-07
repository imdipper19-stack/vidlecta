"""
VidLecta - Email Service
Supports MailerSend API and SMTP fallback
"""
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email service with MailerSend and SMTP support"""
    
    def __init__(self):
        self.mailersend_api_key = getattr(settings, 'MAILERSEND_API_KEY', '')
        self.mailersend_url = "https://api.mailersend.com/v1/email"
        
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email using MailerSend or SMTP fallback"""
        
        # Try MailerSend first
        if self.mailersend_api_key and self.mailersend_api_key.startswith('mlsn.'):
            return await self._send_mailersend(to_email, subject, html_content, text_content)
        
        # Fallback to SMTP
        if settings.SMTP_HOST and settings.SMTP_USER:
            return self._send_smtp(to_email, subject, html_content, text_content)
        
        logger.warning("No email service configured. Email not sent.")
        return False
    
    async def _send_mailersend(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email via MailerSend API"""
        
        payload = {
            "from": {
                "email": getattr(settings, 'MAILERSEND_FROM_EMAIL', 'noreply@vidlecta.com'),
                "name": getattr(settings, 'MAILERSEND_FROM_NAME', 'VidLecta')
            },
            "to": [{"email": to_email}],
            "subject": subject,
            "html": html_content
        }
        
        if text_content:
            payload["text"] = text_content
        
        headers = {
            "Authorization": f"Bearer {self.mailersend_api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.mailersend_url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code in [200, 202]:
                    logger.info(f"Email sent to {to_email} via MailerSend")
                    return True
                else:
                    logger.error(f"MailerSend error: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"MailerSend exception: {str(e)}")
            return False
    
    def _send_smtp(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email via SMTP"""
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USER}>"
        msg["To"] = to_email
        
        if text_content:
            msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(
                    settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
                    to_email,
                    msg.as_string()
                )
                logger.info(f"Email sent to {to_email} via SMTP")
                return True
                
        except Exception as e:
            logger.error(f"SMTP exception: {str(e)}")
            return False
    
    async def send_verification_email(self, to_email: str, token: str, username: str) -> bool:
        """Send email verification link"""
        
        verification_url = f"{settings.FRONTEND_URL}/verify-email.html?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; background: #0f0f14; color: #fff; padding: 40px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #1a1a24; border-radius: 16px; padding: 40px; }}
                .logo {{ font-size: 24px; font-weight: 700; margin-bottom: 32px; }}
                .logo span {{ background: linear-gradient(135deg, #7c3aed, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
                h1 {{ font-size: 24px; margin-bottom: 16px; }}
                p {{ color: #a0a0a0; line-height: 1.6; margin-bottom: 24px; }}
                .btn {{ display: inline-block; background: linear-gradient(135deg, #7c3aed, #3b82f6); color: #fff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; }}
                .footer {{ margin-top: 32px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">▶ <span>VidLecta</span></div>
                <h1>Подтвердите email</h1>
                <p>Привет, {username}!</p>
                <p>Спасибо за регистрацию в VidLecta. Нажмите кнопку ниже, чтобы подтвердить ваш email:</p>
                <p><a href="{verification_url}" class="btn">Подтвердить Email</a></p>
                <p>Или скопируйте ссылку:<br><small>{verification_url}</small></p>
                <p class="footer">Если вы не регистрировались в VidLecta, просто проигнорируйте это письмо.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        VidLecta - Подтверждение Email
        
        Привет, {username}!
        
        Перейдите по ссылке для подтверждения email:
        {verification_url}
        
        Если вы не регистрировались, проигнорируйте это письмо.
        """
        
        return await self.send_email(
            to_email=to_email,
            subject="Подтвердите ваш email — VidLecta",
            html_content=html_content,
            text_content=text_content
        )
    
    async def send_password_reset_email(self, to_email: str, token: str) -> bool:
        """Send password reset link"""
        
        reset_url = f"{settings.FRONTEND_URL}/reset-password.html?token={token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; background: #0f0f14; color: #fff; padding: 40px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #1a1a24; border-radius: 16px; padding: 40px; }}
                .logo {{ font-size: 24px; font-weight: 700; margin-bottom: 32px; }}
                .logo span {{ background: linear-gradient(135deg, #7c3aed, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
                h1 {{ font-size: 24px; margin-bottom: 16px; }}
                p {{ color: #a0a0a0; line-height: 1.6; margin-bottom: 24px; }}
                .btn {{ display: inline-block; background: linear-gradient(135deg, #7c3aed, #3b82f6); color: #fff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; }}
                .footer {{ margin-top: 32px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">▶ <span>VidLecta</span></div>
                <h1>Сброс пароля</h1>
                <p>Вы запросили сброс пароля. Нажмите кнопку ниже:</p>
                <p><a href="{reset_url}" class="btn">Сбросить пароль</a></p>
                <p>Ссылка действительна 1 час.</p>
                <p class="footer">Если вы не запрашивали сброс пароля, проигнорируйте это письмо.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        VidLecta - Сброс пароля
        
        Перейдите по ссылке для сброса пароля:
        {reset_url}
        
        Ссылка действительна 1 час.
        """
        
        return await self.send_email(
            to_email=to_email,
            subject="Сброс пароля — VidLecta",
            html_content=html_content,
            text_content=text_content
        )
    
    async def send_transcription_ready_email(
        self,
        to_email: str,
        video_name: str,
        transcription_url: str
    ) -> bool:
        """Send notification when transcription is ready"""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; background: #0f0f14; color: #fff; padding: 40px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #1a1a24; border-radius: 16px; padding: 40px; }}
                .logo {{ font-size: 24px; font-weight: 700; margin-bottom: 32px; }}
                .logo span {{ background: linear-gradient(135deg, #7c3aed, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
                h1 {{ font-size: 24px; margin-bottom: 16px; }}
                p {{ color: #a0a0a0; line-height: 1.6; margin-bottom: 24px; }}
                .btn {{ display: inline-block; background: linear-gradient(135deg, #7c3aed, #3b82f6); color: #fff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; }}
                .video-name {{ background: #252530; padding: 12px 16px; border-radius: 8px; margin: 16px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">▶ <span>VidLecta</span></div>
                <h1>Транскрипция готова! 🎉</h1>
                <p>Ваше видео успешно обработано:</p>
                <div class="video-name">{video_name}</div>
                <p><a href="{transcription_url}" class="btn">Посмотреть транскрипцию</a></p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Транскрипция готова: {video_name} — VidLecta",
            html_content=html_content
        )


# Global email service instance
email_service = EmailService()
