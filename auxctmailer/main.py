"""Main entry point for AUXCTMailer."""

import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

from auxctmailer.database import MemberDatabase
from auxctmailer.mailer import EmailSender, SendGridEmailSender, EmailTemplate, normalize_template_context
from auxctmailer.logger import setup_logger, get_logger
from auxctmailer.config import load_email_config, EmailConfig
from auxctmailer.exceptions import ConfigError


def parse_filter_criteria(filter_args: list[str] | None) -> dict:
    """Parse filter arguments into a criteria dictionary."""
    if not filter_args:
        return {}
    criteria = {}
    for f in filter_args:
        if '=' in f:
            key, value = f.split('=', 1)
            criteria[key] = value
    return criteria


def create_email_sender(config: EmailConfig):
    """Create the appropriate email sender based on configuration."""
    if config.provider == 'sendgrid':
        return SendGridEmailSender(
            api_key=config.sendgrid_api_key,
            from_email=config.from_email
        )
    return EmailSender(
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        username=config.smtp_user,
        password=config.smtp_password,
        use_tls=config.smtp_use_tls
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description='Send custom emails to AUXCT members'
    )
    parser.add_argument(
        '--training-csv',
        required=True,
        help='Path to CSV file with training/competency records'
    )
    parser.add_argument(
        '--email-csv',
        required=True,
        help='Path to CSV file with member emails'
    )
    parser.add_argument(
        '--courses-csv',
        help='Path to CSV file with course information (optional)'
    )
    parser.add_argument(
        '--units-csv',
        help='Path to CSV file with unit details (optional)'
    )
    parser.add_argument(
        '--extraction-date',
        help='Date when training data was extracted (format: MM/DD/YYYY). If not provided, assumes today.'
    )
    parser.add_argument(
        '--template',
        required=True,
        help='Name of email template file (in templates directory)'
    )
    parser.add_argument(
        '--subject',
        required=True,
        help='Email subject line (can use Jinja2 variables)'
    )
    parser.add_argument(
        '--filter',
        nargs='+',
        metavar='COLUMN=VALUE',
        help='Filter members by column values (e.g., Status=Certified)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be sent without actually sending emails'
    )
    parser.add_argument(
        '--template-dir',
        help='Custom templates directory (default: auxctmailer/templates)'
    )
    parser.add_argument(
        '--save-html',
        help='Directory to save HTML copies of sent emails (optional)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimal logging (WARNING level only)'
    )
    return parser


def handle_dry_run(args, members: list, template: EmailTemplate, logger: logging.Logger) -> int:
    """Handle dry-run mode: preview or generate HTML files without sending.

    Args:
        args: Parsed command line arguments
        members: List of member dictionaries
        template: EmailTemplate instance
        logger: Logger instance

    Returns:
        Exit code (0 for success)
    """
    logger.info("\n=== DRY RUN MODE ===")
    logger.info(f"Would send to {len(members)} recipients")
    logger.info(f"Template: {args.template}")
    logger.info(f"Subject: {args.subject}")

    # If --save-html is specified with --dry-run, generate HTML files without sending
    if args.save_html:
        save_path = Path(args.save_html)
        save_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"\n=== GENERATING HTML FILES ===")
        logger.info(f"Saving to: {save_path}")

        for idx, member in enumerate(members, 1):
            normalized = normalize_template_context(member, args.courses_csv, args.extraction_date)

            # Render the email
            body_html = template.render(args.template, **normalized)

            # Save HTML file
            member_num = normalized.get('member_num', 'unknown')
            first_name = normalized.get('first_name', '')
            last_name = normalized.get('last_name', '')
            filename = f"{member_num}_{first_name}_{last_name}.html".replace(' ', '_')
            file_path = save_path / filename
            file_path.write_text(body_html)

            email = normalized.get('email') or normalized.get('Email', 'N/A')
            logger.info(f"[{idx}/{len(members)}] ✓ Saved HTML for {email} -> {filename}")

        logger.info(f"\n✓ Generated {len(members)} HTML files in {save_path}/")
    else:
        # Show first recipient as example
        if members:
            logger.info("\nExample for first recipient:")
            example = normalize_template_context(members[0], args.courses_csv, args.extraction_date)
            logger.info(f"  To: {example.get('email') or example.get('Email', 'N/A')}")
            subject = template.render_string(args.subject, **example)
            logger.info(f"  Subject: {subject}")
            body = template.render(args.template, **example)
            logger.info(f"  Body preview: {body[:200]}...")

    return 0


def setup_app_logging(verbose: bool, quiet: bool) -> logging.Logger:
    """Configure application logging based on verbosity flags.

    Args:
        verbose: Enable DEBUG level logging
        quiet: Enable WARNING level only logging

    Returns:
        Logger instance for the main module
    """
    if quiet:
        log_level = logging.WARNING
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    setup_logger("auxctmailer", level=log_level)
    setup_logger("auxctmailer.database", level=log_level)
    setup_logger("auxctmailer.mailer", level=log_level)
    return get_logger(__name__)


def main():
    """Main application entry point."""
    parser = build_argument_parser()
    args = parser.parse_args()

    logger = setup_app_logging(verbose=args.verbose, quiet=args.quiet)

    # Load environment variables from .env file
    load_dotenv()

    # Load and validate email configuration (not required for dry-run)
    email_config = None
    if not args.dry_run:
        try:
            email_config = load_email_config()
        except ConfigError as e:
            logger.error(str(e))
            logger.info("(Use --dry-run to test without email configuration)")
            return 1

    # Load member database
    logger.info(f"Loading training data from {args.training_csv}...")
    logger.info(f"Loading email data from {args.email_csv}...")
    if args.units_csv:
        logger.info(f"Loading unit details from {args.units_csv}...")
    db = MemberDatabase(args.training_csv, args.email_csv, args.units_csv)

    # Filter members if criteria provided
    criteria = parse_filter_criteria(args.filter)
    if criteria:
        members = db.filter_members(**criteria)
        logger.info(f"Found {len(members)} members matching filter criteria")
    else:
        members = db.get_all_members()
        logger.info(f"Found {len(members)} total members")

    if not members:
        logger.warning("No members to email")
        return 0

    # Initialize email components
    template = EmailTemplate(args.template_dir)

    if args.dry_run:
        return handle_dry_run(args, members, template, logger)

    # Send emails using configured provider
    logger.info(f"\nSending emails via {email_config.provider.upper()}...")

    sender = create_email_sender(email_config)

    results = sender.send_bulk_emails(
        recipients=members,
        template=template,
        template_name=args.template,
        subject_template=args.subject,
        from_email=email_config.from_email,
        courses_csv=args.courses_csv,
        extraction_date=args.extraction_date,
        save_html_dir=args.save_html
    )

    # Print summary
    logger.info(f"\n=== SUMMARY ===")
    logger.info(f"Successfully sent: {len(results['success'])}")
    logger.info(f"Failed: {len(results['failed'])}")

    if results['failed']:
        logger.warning("\nFailed recipients:")
        for email in results['failed']:
            logger.warning(f"  - {email}")

    return 0 if not results['failed'] else 1


if __name__ == '__main__':
    exit(main())
