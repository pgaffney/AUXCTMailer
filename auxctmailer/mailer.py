"""Email sending and template rendering functionality."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Optional
from jinja2 import Environment, FileSystemLoader, Template
import os
import re
import pandas as pd
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from auxctmailer.exceptions import EmailSendError, TemplateError
from auxctmailer.logger import get_logger
from auxctmailer.context import normalize_template_context  # Import from context module

logger = get_logger(__name__)


# Note: normalize_template_context has been moved to auxctmailer/context.py for better organization
# This import maintains backward compatibility
__all__ = ['EmailTemplate', 'EmailSender', 'SendGridEmailSender', 'normalize_template_context']


class EmailTemplate:
    """Handles email template rendering with Jinja2."""

    def __init__(self, template_dir: Optional[str] = None):
        """Initialize template environment.

        Args:
            template_dir: Directory containing email templates
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"

        self.template_dir = Path(template_dir)
        self.env = Environment(loader=FileSystemLoader(str(self.template_dir)))

    def render(self, template_name: str, **context) -> str:
        """Render a template with given context.

        Args:
            template_name: Name of template file
            **context: Variables to pass to template

        Returns:
            Rendered template string
        """
        template = self.env.get_template(template_name)
        return template.render(**context)

    def render_string(self, template_string: str, **context) -> str:
        """Render a template from string.

        Args:
            template_string: Template as string
            **context: Variables to pass to template

        Returns:
            Rendered template string
        """
        template = Template(template_string)
        return template.render(**context)


class EmailSender:
    """Handles email sending via SMTP."""

    def __init__(self, smtp_host: str, smtp_port: int,
                 username: str, password: str,
                 use_tls: bool = True):
        """Initialize email sender.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            use_tls: Whether to use TLS encryption
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def send_email(self, to_email: str, subject: str,
                   body_html: str, body_text: Optional[str] = None,
                   from_email: Optional[str] = None) -> bool:
        """Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML email body
            body_text: Plain text email body (optional)
            from_email: Sender email (defaults to username)

        Returns:
            True if sent successfully, False otherwise
        """
        if from_email is None:
            from_email = self.username

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email

        # Attach plain text and HTML versions
        if body_text:
            msg.attach(MIMEText(body_text, 'plain'))
        msg.attach(MIMEText(body_html, 'html'))

        try:
            # Connect to SMTP server
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)

            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()

            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_bulk_emails(self, recipients: List[Dict],
                        template: EmailTemplate,
                        template_name: str,
                        subject_template: str,
                        from_email: Optional[str] = None,
                        courses_csv: Optional[str] = None,
                        extraction_date: Optional[str] = None,
                        save_html_dir: Optional[str] = None) -> Dict[str, List[str]]:
        """Send personalized emails to multiple recipients.

        Args:
            recipients: List of recipient dictionaries with email and template context
            template: EmailTemplate instance
            template_name: Name of email template file
            subject_template: Subject line template string
            from_email: Sender email (defaults to username)
            courses_csv: Optional path to courses CSV file
            extraction_date: Optional extraction date (MM/DD/YYYY)
            save_html_dir: Optional directory to save HTML copies of sent emails

        Returns:
            Dictionary with 'success' and 'failed' lists of email addresses
        """
        results = {'success': [], 'failed': []}
        total = len(recipients)

        # Create save directory if specified
        if save_html_dir:
            save_path = Path(save_html_dir)
            save_path.mkdir(parents=True, exist_ok=True)

        for idx, recipient in enumerate(recipients, 1):
            # Normalize keys for template compatibility
            normalized_recipient = normalize_template_context(recipient, courses_csv, extraction_date)

            email = normalized_recipient.get('email') or normalized_recipient.get('Email')
            if not email:
                continue

            # Render subject and body with recipient data
            subject = template.render_string(subject_template, **normalized_recipient)
            body_html = template.render(template_name, **normalized_recipient)

            # Send email
            success = self.send_email(
                to_email=email,
                subject=subject,
                body_html=body_html,
                from_email=from_email
            )

            if success:
                results['success'].append(email)
                logger.info(f"[{idx}/{total}] ✓ Sent to {email}")

                # Save HTML copy if directory specified
                if save_html_dir:
                    member_num = normalized_recipient.get('member_num', 'unknown')
                    first_name = normalized_recipient.get('first_name', '')
                    last_name = normalized_recipient.get('last_name', '')
                    filename = f"{member_num}_{first_name}_{last_name}.html".replace(' ', '_')
                    file_path = save_path / filename
                    file_path.write_text(body_html)
            else:
                results['failed'].append(email)
                logger.warning(f"[{idx}/{total}] ✗ Failed to send to {email}")

        return results


class SendGridEmailSender:
    """Handles email sending via SendGrid API."""

    def __init__(self, api_key: str, from_email: str):
        """Initialize SendGrid email sender.

        Args:
            api_key: SendGrid API key
            from_email: Default sender email address
        """
        self.api_key = api_key
        self.from_email = from_email
        self.client = SendGridAPIClient(api_key)

    def send_email(self, to_email: str, subject: str,
                   body_html: str, body_text: Optional[str] = None,
                   from_email: Optional[str] = None) -> bool:
        """Send an email via SendGrid.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML email body
            body_text: Plain text email body (optional)
            from_email: Sender email (defaults to configured from_email)

        Returns:
            True if sent successfully, False otherwise
        """
        if from_email is None:
            from_email = self.from_email

        try:
            message = Mail(
                from_email=Email(from_email),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", body_html)
            )

            if body_text:
                message.plain_text_content = Content("text/plain", body_text)

            response = self.client.send(message)

            # SendGrid returns 202 for successful acceptance
            return response.status_code == 202

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_bulk_emails(self, recipients: List[Dict],
                        template: EmailTemplate,
                        template_name: str,
                        subject_template: str,
                        from_email: Optional[str] = None,
                        courses_csv: Optional[str] = None,
                        extraction_date: Optional[str] = None,
                        save_html_dir: Optional[str] = None) -> Dict[str, List[str]]:
        """Send personalized emails to multiple recipients via SendGrid.

        Args:
            recipients: List of recipient dictionaries with email and template context
            template: EmailTemplate instance
            template_name: Name of email template file
            subject_template: Subject line template string
            from_email: Sender email (defaults to configured from_email)
            courses_csv: Optional path to courses CSV file
            extraction_date: Optional extraction date (MM/DD/YYYY)
            save_html_dir: Optional directory to save HTML copies of sent emails

        Returns:
            Dictionary with 'success' and 'failed' lists of email addresses
        """
        results = {'success': [], 'failed': []}
        total = len(recipients)

        # Create save directory if specified
        if save_html_dir:
            save_path = Path(save_html_dir)
            save_path.mkdir(parents=True, exist_ok=True)

        for idx, recipient in enumerate(recipients, 1):
            # Normalize keys for template compatibility
            normalized_recipient = normalize_template_context(recipient, courses_csv, extraction_date)

            email = normalized_recipient.get('email') or normalized_recipient.get('Email')
            if not email:
                continue

            # Render subject and body with recipient data
            subject = template.render_string(subject_template, **normalized_recipient)
            body_html = template.render(template_name, **normalized_recipient)

            # Send email
            success = self.send_email(
                to_email=email,
                subject=subject,
                body_html=body_html,
                from_email=from_email
            )

            if success:
                results['success'].append(email)
                logger.info(f"[{idx}/{total}] ✓ Sent to {email}")

                # Save HTML copy if directory specified
                if save_html_dir:
                    member_num = normalized_recipient.get('member_num', 'unknown')
                    first_name = normalized_recipient.get('first_name', '')
                    last_name = normalized_recipient.get('last_name', '')
                    filename = f"{member_num}_{first_name}_{last_name}.html".replace(' ', '_')
                    file_path = save_path / filename
                    file_path.write_text(body_html)
            else:
                results['failed'].append(email)
                logger.warning(f"[{idx}/{total}] ✗ Failed to send to {email}")

        return results
