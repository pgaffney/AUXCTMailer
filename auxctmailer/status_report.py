"""Entry point for sending task status report emails from xlsx data."""

import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

from auxctmailer.xlsx_loader import (
    XlsxTaskLoader,
    load_competency_summary,
    load_member_info,
    merge_competency_data,
)
from auxctmailer.mailer import EmailSender, SendGridEmailSender, EmailTemplate
from auxctmailer.logger import setup_logger, get_logger
from auxctmailer.config import load_email_config, EmailConfig
from auxctmailer.exceptions import ConfigError


def build_argument_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description='Send task status report emails to members from xlsx export'
    )
    parser.add_argument(
        '--xlsx',
        required=True,
        help='Path to xlsx file with member task data (To Do Lists export)'
    )
    parser.add_argument(
        '--competencies-xlsx',
        help='Path to xlsx file with competency status dates (Unit Summary - Competencies export)'
    )
    parser.add_argument(
        '--members-xlsx',
        help='Path to xlsx file with member info (Unit Members export with email, phone, uniform status)'
    )
    parser.add_argument(
        '--email-csv',
        required=True,
        help='Path to CSV file with member emails'
    )
    parser.add_argument(
        '--units-csv',
        help='Path to CSV file with unit details (optional, for unit name lookup)'
    )
    parser.add_argument(
        '--template',
        default='task_status_report.html',
        help='Name of email template file (default: task_status_report.html)'
    )
    parser.add_argument(
        '--subject',
        default='Task Status Report - {{ first_name_titlecase }} {{ last_name }}',
        help='Email subject line (can use Jinja2 variables)'
    )
    parser.add_argument(
        '--filter-member',
        metavar='MEMBER_ID',
        help='Send only to specific member ID (for testing)'
    )
    parser.add_argument(
        '--filter-has-red',
        action='store_true',
        help='Only send to members with urgent (red) tasks'
    )
    parser.add_argument(
        '--filter-has-yellow',
        action='store_true',
        help='Only send to members with attention-needed (yellow) tasks'
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
        help='Directory to save HTML copies of sent emails (optional but recommended)'
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


def setup_app_logging(verbose: bool, quiet: bool) -> logging.Logger:
    """Configure application logging based on verbosity flags."""
    if quiet:
        log_level = logging.WARNING
    elif verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    setup_logger("auxctmailer", level=log_level)
    setup_logger("auxctmailer.xlsx_loader", level=log_level)
    setup_logger("auxctmailer.mailer", level=log_level)
    return get_logger(__name__)


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


def load_unit_details(units_csv: str, logger: logging.Logger) -> dict:
    """Load unit details from CSV for name lookup."""
    import pandas as pd

    units = {}
    if not units_csv or not Path(units_csv).exists():
        return units

    try:
        df = pd.read_csv(units_csv, dtype={'Unit Number': str})
        for _, row in df.iterrows():
            unit_num = str(row.get('Unit Number', '')).strip()
            if unit_num and unit_num != 'nan':
                units[unit_num] = {
                    'unit_name': row.get('Unit Name', ''),
                    'unit_name_pretty': prettify_unit_name(row.get('Unit Name', '')),
                    'fso_is': row.get('FSO-IS', ''),
                    'fso_mt': row.get('FSO-MT', ''),
                }
        logger.info(f"Loaded {len(units)} unit details")
    except Exception as e:
        logger.warning(f"Could not load unit details: {e}")

    return units


def prettify_unit_name(raw_name: str) -> str:
    """Convert raw unit name to pretty format."""
    if not raw_name or str(raw_name).lower() == 'nan':
        return ''

    pretty = str(raw_name).strip().title()

    # Remove common flotilla abbreviations from the end
    flotilla_abbrevs = [' Flotilla', ' Flot', ' Flot.', ' Flt', ' Flt.']
    for abbrev in flotilla_abbrevs:
        if pretty.endswith(abbrev):
            pretty = pretty[:-len(abbrev)].strip()
            break

    # Always ensure it ends with "Flotilla"
    if not pretty.endswith('Flotilla'):
        pretty = pretty + ' Flotilla'

    return pretty


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

    # Load member task data from xlsx
    logger.info(f"Loading task data from {args.xlsx}...")
    loader = XlsxTaskLoader(args.xlsx, args.email_csv)
    members = loader.load()
    logger.info(f"Loaded {len(members)} members")

    # Load unit details if provided
    unit_details = load_unit_details(args.units_csv, logger) if args.units_csv else {}

    # Load all competency data if provided (for complete qualifications list)
    competency_data = load_competency_summary(args.competencies_xlsx) if args.competencies_xlsx else {}

    # Load member info if provided (for enhanced member info box)
    member_info_data = load_member_info(args.members_xlsx) if args.members_xlsx else {}

    # Get members with email addresses
    members_with_email = loader.get_members_with_email()
    logger.info(f"Found {len(members_with_email)} members with email addresses")

    # Apply filters
    filtered_members = members_with_email

    if args.filter_member:
        filtered_members = [m for m in filtered_members if m.member_id == args.filter_member]
        logger.info(f"Filtered to member {args.filter_member}: {len(filtered_members)} found")

    if args.filter_has_red:
        filtered_members = [m for m in filtered_members if m.to_template_context()['has_red_tasks']]
        logger.info(f"Filtered to members with red tasks: {len(filtered_members)}")

    if args.filter_has_yellow:
        # Include members with yellow OR red tasks
        filtered_members = [
            m for m in filtered_members
            if m.to_template_context()['has_yellow_tasks'] or m.to_template_context()['has_red_tasks']
        ]
        logger.info(f"Filtered to members with yellow/red tasks: {len(filtered_members)}")

    if not filtered_members:
        logger.warning("No members to email after filtering")
        return 0

    # Initialize template
    template = EmailTemplate(args.template_dir)

    # Prepare recipients with template context
    recipients = []
    for member in filtered_members:
        ctx = member.to_template_context()

        # Add unit details if available
        if member.unit_number in unit_details:
            unit = unit_details[member.unit_number]
            ctx['unit_name'] = unit['unit_name']
            ctx['unit_name_pretty'] = unit['unit_name_pretty']
            ctx['fso_is'] = unit['fso_is']
            ctx['fso_mt'] = unit['fso_mt']

        # Merge competency data from Unit Summary xlsx (complete list with dates)
        if competency_data and member.member_id in competency_data:
            ctx['competencies'] = merge_competency_data(
                task_competencies=ctx.get('competencies', []),
                summary_competencies=competency_data[member.member_id],
            )

        # Add enhanced member info if available
        if member_info_data and member.member_id in member_info_data:
            info = member_info_data[member.member_id]
            ctx['member_status'] = info.get('member_status')
            ctx['member_status_date'] = info.get('member_status_date')
            ctx['email_on_file'] = info.get('email')
            ctx['mobile_phone'] = info.get('mobile')
            ctx['home_phone'] = info.get('home_phone')
            ctx['uniform_last_inspected'] = info.get('uniform_last_inspected')
            ctx['uniform_exempt'] = info.get('uniform_exempt')
            ctx['uniform_current_year'] = info.get('uniform_current_year')

        recipients.append(ctx)

    if args.dry_run:
        return handle_dry_run(args, recipients, template, logger)

    # Send emails
    logger.info(f"\nSending emails via {email_config.provider.upper()}...")

    sender = create_email_sender(email_config)

    # Create save directory if specified
    save_path = None
    if args.save_html:
        save_path = Path(args.save_html)
        save_path.mkdir(parents=True, exist_ok=True)

    results = {'success': [], 'failed': []}
    total = len(recipients)

    for idx, recipient in enumerate(recipients, 1):
        email = recipient.get('email')
        if not email:
            continue

        # Render subject and body
        subject = template.render_string(args.subject, **recipient)
        body_html = template.render(args.template, **recipient)

        # Send email
        success = sender.send_email(
            to_email=email,
            subject=subject,
            body_html=body_html,
            from_email=email_config.from_email
        )

        if success:
            results['success'].append(email)
            logger.info(f"[{idx}/{total}] Sent to {email}")

            # Save HTML copy if directory specified
            if save_path:
                member_num = recipient.get('member_num', 'unknown')
                first_name = recipient.get('first_name', '')
                last_name = recipient.get('last_name', '')
                filename = f"{last_name}_{first_name}_{member_num}.html".replace(' ', '_')
                file_path = save_path / filename
                file_path.write_text(body_html)
        else:
            results['failed'].append(email)
            logger.warning(f"[{idx}/{total}] Failed to send to {email}")

    # Print summary
    logger.info(f"\n=== SUMMARY ===")
    logger.info(f"Successfully sent: {len(results['success'])}")
    logger.info(f"Failed: {len(results['failed'])}")

    if results['failed']:
        logger.warning("\nFailed recipients:")
        for email in results['failed']:
            logger.warning(f"  - {email}")

    return 0 if not results['failed'] else 1


def handle_dry_run(args, recipients: list, template: EmailTemplate, logger: logging.Logger) -> int:
    """Handle dry-run mode: preview or generate HTML files without sending."""
    logger.info("\n=== DRY RUN MODE ===")
    logger.info(f"Would send to {len(recipients)} recipients")
    logger.info(f"Template: {args.template}")
    logger.info(f"Subject: {args.subject}")

    # Count task types
    total_red = sum(len(r['tasks_red']) for r in recipients)
    total_yellow = sum(len(r['tasks_yellow']) for r in recipients)
    total_green = sum(len(r['tasks_green']) for r in recipients)

    logger.info(f"\nTask summary across all recipients:")
    logger.info(f"  Red (urgent): {total_red} tasks")
    logger.info(f"  Yellow (attention): {total_yellow} tasks")
    logger.info(f"  Green (good): {total_green} tasks")

    # If --save-html is specified with --dry-run, generate HTML files without sending
    if args.save_html:
        save_path = Path(args.save_html)
        save_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"\n=== GENERATING HTML FILES ===")
        logger.info(f"Saving to: {save_path}")

        for idx, recipient in enumerate(recipients, 1):
            # Render the email
            body_html = template.render(args.template, **recipient)

            # Save HTML file
            member_num = recipient.get('member_num', 'unknown')
            first_name = recipient.get('first_name', '')
            last_name = recipient.get('last_name', '')
            filename = f"{last_name}_{first_name}_{member_num}.html".replace(' ', '_')
            file_path = save_path / filename
            file_path.write_text(body_html)

            email = recipient.get('email', 'N/A')
            logger.info(f"[{idx}/{len(recipients)}] Saved HTML for {email} -> {filename}")

        logger.info(f"\nGenerated {len(recipients)} HTML files in {save_path}/")
    else:
        # Show first recipient as example
        if recipients:
            logger.info("\nExample for first recipient:")
            example = recipients[0]
            logger.info(f"  To: {example.get('email', 'N/A')}")
            logger.info(f"  Name: {example.get('first_name')} {example.get('last_name')}")
            logger.info(f"  Red tasks: {len(example['tasks_red'])}")
            logger.info(f"  Yellow tasks: {len(example['tasks_yellow'])}")
            logger.info(f"  Green tasks: {len(example['tasks_green'])}")

            subject = template.render_string(args.subject, **example)
            logger.info(f"  Subject: {subject}")

    return 0


if __name__ == '__main__':
    exit(main())
