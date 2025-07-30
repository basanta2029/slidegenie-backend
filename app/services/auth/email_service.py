"""
Email Validation and Notification Service for SlideGenie.

Handles academic email validation, institution verification,
and email notifications for authentication workflows.
"""
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Set
import re
import aiohttp
import structlog

from app.core.config import get_settings
from app.core.exceptions import InvalidCredentialsError, EmailDeliveryError
from app.services.auth.academic_validator import AcademicEmailValidator

logger = structlog.get_logger(__name__)
settings = get_settings()


class EmailValidationService:
    """Service for email validation and notifications."""
    
    def __init__(self):
        self.academic_validator = AcademicEmailValidator()
        self._known_academic_domains: Set[str] = set()
        self._domain_cache: Dict[str, Optional[str]] = {}
    
    async def validate_academic_email(self, email: str) -> Optional[str]:
        """
        Validate academic email and return institution name.
        
        Args:
            email: Email address to validate
            
        Returns:
            Institution name if academic email, None otherwise
            
        Raises:
            InvalidCredentialsError: If email domain is not academic
        """
        try:
            domain = email.split('@')[1].lower()
            
            # Check cache first
            if domain in self._domain_cache:
                return self._domain_cache[domain]
            
            # Use academic validator
            institution = await self.academic_validator.validate_domain(domain)
            
            # Cache result
            self._domain_cache[domain] = institution
            
            if institution:
                self._known_academic_domains.add(domain)
                logger.info(
                    "academic_email_validated",
                    domain=domain,
                    institution=institution
                )
                return institution
            else:
                # For SlideGenie, we'll allow non-academic emails but log them
                logger.info(
                    "non_academic_email_registered",
                    domain=domain,
                    email=email
                )
                return None
                
        except Exception as e:
            logger.error(
                "email_validation_error",
                error=str(e),
                email=email
            )
            # Don't block registration for validation errors
            return None
    
    def is_academic_email(self, email: str) -> bool:
        """
        Check if email is from an academic domain.
        
        Args:
            email: Email address to check
            
        Returns:
            True if academic email, False otherwise
        """
        try:
            domain = email.split('@')[1].lower()
            return domain in self._known_academic_domains or domain.endswith('.edu')
        except IndexError:
            return False
    
    async def send_verification_email(
        self,
        email: str,
        full_name: str,
        verification_token: str,
    ) -> bool:
        """
        Send email verification message.
        
        Args:
            email: Recipient email address
            full_name: User's full name
            verification_token: Verification token
            
        Returns:
            Success status
            
        Raises:
            EmailDeliveryError: If email sending fails
        """
        try:
            # Build verification URL
            base_url = "https://app.slidegenie.com"  # TODO: Get from config
            verification_url = f"{base_url}/verify-email?token={verification_token}"
            
            # Email content
            subject = "Verify your SlideGenie account"
            
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Verify Your SlideGenie Account</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #2563eb;">SlideGenie</h1>
            <p style="font-size: 18px; color: #666;">Academic Presentation Generator</p>
        </div>
        
        <h2>Welcome to SlideGenie, {full_name}!</h2>
        
        <p>Thank you for registering with SlideGenie. To complete your account setup and start creating professional academic presentations, please verify your email address.</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}" 
               style="background-color: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                Verify Email Address
            </a>
        </div>
        
        <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
        <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
            {verification_url}
        </p>
        
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
        
        <h3>What's Next?</h3>
        <ul>
            <li><strong>Create presentations:</strong> Generate slides from your research papers, abstracts, or outlines</li>
            <li><strong>Use academic templates:</strong> Choose from conference-specific and institution templates</li>
            <li><strong>Export to multiple formats:</strong> PowerPoint, PDF, LaTeX, and more</li>
            <li><strong>Manage references:</strong> Automatic citation formatting and bibliography generation</li>
        </ul>
        
        <p style="margin-top: 30px; font-size: 14px; color: #666;">
            This verification link will expire in 24 hours. If you didn't create a SlideGenie account, you can safely ignore this email.
        </p>
        
        <div style="margin-top: 40px; text-align: center; font-size: 12px; color: #999;">
            <p>&copy; 2024 SlideGenie. All rights reserved.</p>
            <p>
                <a href="https://slidegenie.com/privacy" style="color: #999;">Privacy Policy</a> | 
                <a href="https://slidegenie.com/terms" style="color: #999;">Terms of Service</a>
            </p>
        </div>
    </div>
</body>
</html>
            """
            
            text_body = f"""
Welcome to SlideGenie, {full_name}!

Thank you for registering with SlideGenie. To complete your account setup and start creating professional academic presentations, please verify your email address.

Verification Link: {verification_url}

What's Next?
- Create presentations: Generate slides from your research papers, abstracts, or outlines
- Use academic templates: Choose from conference-specific and institution templates  
- Export to multiple formats: PowerPoint, PDF, LaTeX, and more
- Manage references: Automatic citation formatting and bibliography generation

This verification link will expire in 24 hours. If you didn't create a SlideGenie account, you can safely ignore this email.

© 2024 SlideGenie. All rights reserved.
            """
            
            success = await self._send_email(
                to_email=email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "verification_email_sent",
                email=email,
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "verification_email_error",
                error=str(e),
                email=email
            )
            raise EmailDeliveryError(f"Failed to send verification email: {str(e)}")
    
    async def send_password_reset_email(
        self,
        email: str,
        full_name: str,
        reset_token: str,
    ) -> bool:
        """
        Send password reset email.
        
        Args:
            email: Recipient email address
            full_name: User's full name
            reset_token: Password reset token
            
        Returns:
            Success status
        """
        try:
            # Build reset URL
            base_url = "https://app.slidegenie.com"  # TODO: Get from config
            reset_url = f"{base_url}/reset-password?token={reset_token}"
            
            subject = "Reset your SlideGenie password"
            
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reset Your SlideGenie Password</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #2563eb;">SlideGenie</h1>
        </div>
        
        <h2>Password Reset Request</h2>
        
        <p>Hello {full_name},</p>
        
        <p>We received a request to reset the password for your SlideGenie account. If you made this request, click the button below to reset your password:</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" 
               style="background-color: #dc2626; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                Reset Password
            </a>
        </div>
        
        <p>If the button doesn't work, copy and paste this link into your browser:</p>
        <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
            {reset_url}
        </p>
        
        <p style="margin-top: 30px; color: #dc2626; font-weight: bold;">
            This reset link will expire in 1 hour for security reasons.
        </p>
        
        <p style="margin-top: 20px; font-size: 14px; color: #666;">
            If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.
        </p>
        
        <div style="margin-top: 40px; text-align: center; font-size: 12px; color: #999;">
            <p>&copy; 2024 SlideGenie. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
            """
            
            text_body = f"""
Password Reset Request

Hello {full_name},

We received a request to reset the password for your SlideGenie account. If you made this request, use the link below to reset your password:

Reset Link: {reset_url}

This reset link will expire in 1 hour for security reasons.

If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.

© 2024 SlideGenie. All rights reserved.
            """
            
            success = await self._send_email(
                to_email=email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )
            
            logger.info(
                "password_reset_email_sent",
                email=email,
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "password_reset_email_error",
                error=str(e),
                email=email
            )
            raise EmailDeliveryError(f"Failed to send password reset email: {str(e)}")
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """
        Send email using SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            
        Returns:
            Success status
        """
        if not all([settings.SMTP_HOST, settings.SMTP_USER, settings.SMTP_PASSWORD]):
            logger.warning("smtp_not_configured")
            return True  # In development, pretend emails are sent
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg['To'] = to_email
            
            # Add text and HTML parts
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(
                "smtp_send_error",
                error=str(e),
                to_email=to_email
            )
            return False
    
    async def get_domain_suggestions(self, partial_domain: str) -> List[str]:
        """
        Get academic domain suggestions for autocomplete.
        
        Args:
            partial_domain: Partial domain name
            
        Returns:
            List of suggested academic domains
        """
        suggestions = []
        
        # Get suggestions from academic validator
        validator_suggestions = await self.academic_validator.get_domain_suggestions(
            partial_domain
        )
        suggestions.extend(validator_suggestions)
        
        # Add known domains that match
        for domain in self._known_academic_domains:
            if partial_domain.lower() in domain and domain not in suggestions:
                suggestions.append(domain)
        
        return sorted(suggestions[:10])  # Return top 10 matches


class EmailTemplateService:
    """Service for managing email templates."""
    
    def __init__(self):
        self.templates: Dict[str, Dict[str, str]] = {
            "welcome": {
                "subject": "Welcome to SlideGenie!",
                "template": "welcome_email.html"
            },
            "password_changed": {
                "subject": "Your SlideGenie password has been changed",
                "template": "password_changed.html"
            },
            "subscription_reminder": {
                "subject": "Your SlideGenie subscription expires soon",
                "template": "subscription_reminder.html"
            }
        }
    
    def get_template(self, template_name: str) -> Optional[Dict[str, str]]:
        """Get email template configuration."""
        return self.templates.get(template_name)
    
    def render_template(
        self,
        template_name: str,
        variables: Dict[str, str]
    ) -> Dict[str, str]:
        """Render email template with variables."""
        template_config = self.get_template(template_name)
        if not template_config:
            raise ValueError(f"Template not found: {template_name}")
        
        # In a real implementation, you'd use a template engine like Jinja2
        # For now, simple string replacement
        subject = template_config["subject"]
        for key, value in variables.items():
            subject = subject.replace(f"{{{key}}}", value)
        
        return {
            "subject": subject,
            "html_body": "",  # Would load from file
            "text_body": "",  # Would load from file
        }