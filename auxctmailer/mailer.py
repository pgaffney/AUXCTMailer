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


def normalize_template_context(data: Dict, courses_csv: Optional[str] = None, extraction_date: Optional[str] = None) -> Dict:
    """Normalize dictionary keys to be template-friendly.

    Converts keys like "First Name" to "first_name" and "Member #" to "member_num".
    Also adds current year information and course status for date logic.

    Args:
        data: Dictionary with potentially problematic keys
        courses_csv: Optional path to courses CSV file
        extraction_date: Optional extraction date string (MM/DD/YYYY) - date when training data was extracted

    Returns:
        Dictionary with normalized keys (also keeps original keys)
    """
    from datetime import datetime, timedelta

    normalized = dict(data)  # Keep original keys

    # Determine the reference date for days_until_due calculations
    if extraction_date:
        try:
            reference_date = datetime.strptime(extraction_date, "%m/%d/%Y")
        except ValueError:
            # If invalid format, fall back to today
            reference_date = datetime.now()
    else:
        reference_date = datetime.now()

    for key, value in data.items():
        # Create a normalized version of the key
        normalized_key = key.lower().replace(' ', '_').replace('#', 'num').replace('?', '').replace('/', '_')
        # Remove any other special characters
        normalized_key = re.sub(r'[^\w_]', '', normalized_key)
        normalized[normalized_key] = value

    # Add current year information for template logic
    now = datetime.now()
    normalized['current_year'] = now.year
    normalized['current_year_start'] = f"1/1/{now.year}"
    normalized['current_year_end'] = f"12/31/{now.year}"

    # Add extraction date to context
    normalized['extraction_date'] = extraction_date if extraction_date else reference_date.strftime("%m/%d/%Y")

    # Parse uniform inspection date and check if it needs renewal
    uniform_inspection = normalized.get('uniform_inspection') or normalized.get('Uniform Inspection')
    needs_inspection = True  # Default to needing inspection

    # Check if uniform_inspection is NaN or empty
    if uniform_inspection and str(uniform_inspection).strip() and str(uniform_inspection).lower() != 'nan':
        try:
            # Try to parse the date (handles formats like "2/20/2024", "2/18/2025", etc.)
            inspection_date = datetime.strptime(str(uniform_inspection).strip(), "%m/%d/%Y")
            year_start = datetime(now.year, 1, 1)
            # If inspection is this year or later, they don't need a new one
            needs_inspection = inspection_date < year_start
        except (ValueError, AttributeError):
            # If we can't parse the date, assume they need inspection
            needs_inspection = True
            uniform_inspection = None
    else:
        # Clear NaN or empty values
        uniform_inspection = None

    # Update the normalized dict with cleaned value
    normalized['uniform_inspection'] = uniform_inspection
    normalized['needs_uniform_inspection'] = needs_inspection

    # Process course requirements if courses CSV is provided
    normalized['courses_overdue'] = []
    normalized['courses_due_soon'] = []

    if courses_csv and os.path.exists(courses_csv):
        try:
            courses_df = pd.read_csv(courses_csv)

            for _, course in courses_df.iterrows():
                code = str(course['Code']).strip()
                title = course['Title']
                url = course['URL']
                enrollment_code = course.get('EnrollmentCode', '')

                # Get days until due from the member's record
                days_until_due = normalized.get(code)

                if days_until_due is not None and pd.notna(days_until_due):
                    try:
                        days = int(float(days_until_due))

                        # Calculate the actual due date from extraction date + days
                        actual_due_date = reference_date + timedelta(days=days)

                        # Calculate days from TODAY to the due date
                        days_from_today = (actual_due_date - now).days

                        # Special case: Certain courses with days=0 are due 12/31 of current year
                        # SP_100643: Suicide Prevention
                        # CRA_502319: Civil Rights Awareness
                        # SAPRR_502379: Sexual Assault Prevention, Response, and Recovery
                        if code in ['SP_100643', 'CRA_502319', 'SAPRR_502379'] and days == 0:
                            year_end = datetime(now.year, 12, 31)
                            normalized['courses_due_soon'].append({
                                'code': code,
                                'title': title,
                                'url': url,
                                'enrollment_code': enrollment_code,
                                'days_until_due': (year_end - now).days,
                                'due_date': year_end.strftime("%m/%d/%Y")
                            })
                        elif days_from_today < 0:
                            # Course is overdue (due date has passed)
                            normalized['courses_overdue'].append({
                                'code': code,
                                'title': title,
                                'url': url,
                                'enrollment_code': enrollment_code,
                                'days_overdue': abs(days_from_today)
                            })
                        elif 0 <= days_from_today <= 365:
                            # Course is due soon (within next 365 days)
                            normalized['courses_due_soon'].append({
                                'code': code,
                                'title': title,
                                'url': url,
                                'enrollment_code': enrollment_code,
                                'days_until_due': days_from_today,
                                'due_date': actual_due_date.strftime("%m/%d/%Y")
                            })
                        # If days_from_today > 365, don't add any warning
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            # If we can't load courses, just continue without course warnings
            pass

    normalized['has_overdue_courses'] = len(normalized['courses_overdue']) > 0
    normalized['has_due_soon_courses'] = len(normalized['courses_due_soon']) > 0

    return normalized


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
            print(f"Failed to send email to {to_email}: {e}")
            return False

    def send_bulk_emails(self, recipients: List[Dict],
                        template: EmailTemplate,
                        template_name: str,
                        subject_template: str,
                        from_email: Optional[str] = None,
                        courses_csv: Optional[str] = None,
                        extraction_date: Optional[str] = None) -> Dict[str, List[str]]:
        """Send personalized emails to multiple recipients.

        Args:
            recipients: List of recipient dictionaries with email and template context
            template: EmailTemplate instance
            template_name: Name of email template file
            subject_template: Subject line template string
            from_email: Sender email (defaults to username)
            courses_csv: Optional path to courses CSV file
            extraction_date: Optional extraction date (MM/DD/YYYY)

        Returns:
            Dictionary with 'success' and 'failed' lists of email addresses
        """
        results = {'success': [], 'failed': []}

        for recipient in recipients:
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
                print(f"✓ Sent to {email}")
            else:
                results['failed'].append(email)
                print(f"✗ Failed to send to {email}")

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
            print(f"Failed to send email to {to_email}: {e}")
            return False

    def send_bulk_emails(self, recipients: List[Dict],
                        template: EmailTemplate,
                        template_name: str,
                        subject_template: str,
                        from_email: Optional[str] = None,
                        courses_csv: Optional[str] = None,
                        extraction_date: Optional[str] = None) -> Dict[str, List[str]]:
        """Send personalized emails to multiple recipients via SendGrid.

        Args:
            recipients: List of recipient dictionaries with email and template context
            template: EmailTemplate instance
            template_name: Name of email template file
            subject_template: Subject line template string
            from_email: Sender email (defaults to configured from_email)
            courses_csv: Optional path to courses CSV file
            extraction_date: Optional extraction date (MM/DD/YYYY)

        Returns:
            Dictionary with 'success' and 'failed' lists of email addresses
        """
        results = {'success': [], 'failed': []}

        for recipient in recipients:
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
                print(f"✓ Sent to {email}")
            else:
                results['failed'].append(email)
                print(f"✗ Failed to send to {email}")

        return results
