"""Main entry point for AUXCTMailer."""

import argparse
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

from auxctmailer.database import MemberDatabase
from auxctmailer.mailer import EmailSender, SendGridEmailSender, EmailTemplate, normalize_template_context
from auxctmailer.logger import setup_logger, get_logger


def main():
    """Main application entry point."""
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

    args = parser.parse_args()

    # Setup logging
    if args.quiet:
        log_level = logging.WARNING
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    setup_logger("auxctmailer", level=log_level)
    setup_logger("auxctmailer.database", level=log_level)
    setup_logger("auxctmailer.mailer", level=log_level)
    logger = get_logger(__name__)

    # Load environment variables from .env file
    load_dotenv()

    # Get email provider configuration
    email_provider = os.getenv('EMAIL_PROVIDER', 'sendgrid').lower()
    from_email = os.getenv('FROM_EMAIL')

    # Validate configuration (not required for dry-run)
    if not args.dry_run:
        if email_provider == 'sendgrid':
            sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
            if not sendgrid_api_key or not from_email:
                logger.error("SendGrid configuration missing in environment variables")
                logger.error("Required: SENDGRID_API_KEY, FROM_EMAIL")
                logger.info("(Use --dry-run to test without email configuration)")
                return 1
        elif email_provider == 'smtp':
            smtp_host = os.getenv('SMTP_HOST')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_user = os.getenv('SMTP_USER')
            smtp_pass = os.getenv('SMTP_PASSWORD')
            smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() in ('true', '1', 'yes')

            # FROM_EMAIL defaults to SMTP_USER if not specified
            if not from_email:
                from_email = smtp_user

            if not all([smtp_host, smtp_user, smtp_pass]):
                logger.error("SMTP configuration missing in environment variables")
                logger.error("Required: SMTP_HOST, SMTP_USER, SMTP_PASSWORD")
                logger.info("Optional: SMTP_PORT (default: 587), SMTP_USE_TLS (default: true), FROM_EMAIL (default: SMTP_USER)")
                logger.info("(Use --dry-run to test without SMTP configuration)")
                return 1
        else:
            logger.error(f"Unknown email provider '{email_provider}'")
            logger.error("Set EMAIL_PROVIDER to 'sendgrid' or 'smtp'")
            return 1

    # Load member database
    logger.info(f"Loading training data from {args.training_csv}...")
    logger.info(f"Loading email data from {args.email_csv}...")
    if args.units_csv:
        logger.info(f"Loading unit details from {args.units_csv}...")
    db = MemberDatabase(args.training_csv, args.email_csv, args.units_csv)

    # Filter members if criteria provided
    if args.filter:
        criteria = {}
        for f in args.filter:
            if '=' in f:
                key, value = f.split('=', 1)
                criteria[key] = value

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
        logger.info("\n=== DRY RUN MODE ===")
        logger.info(f"Would send to {len(members)} recipients")
        logger.info(f"Template: {args.template}")
        logger.info(f"Subject: {args.subject}")

        # If --save-html is specified with --dry-run, generate HTML files without sending
        if args.save_html:
            from pathlib import Path
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

    # Send emails using configured provider
    logger.info(f"\nSending emails via {email_provider.upper()}...")

    if email_provider == 'sendgrid':
        sender = SendGridEmailSender(
            api_key=sendgrid_api_key,
            from_email=from_email
        )
    else:  # smtp
        sender = EmailSender(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            username=smtp_user,
            password=smtp_pass,
            use_tls=smtp_use_tls
        )

    results = sender.send_bulk_emails(
        recipients=members,
        template=template,
        template_name=args.template,
        subject_template=args.subject,
        from_email=from_email,
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
