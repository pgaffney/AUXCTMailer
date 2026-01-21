"""Entry point for sending task status report emails from xlsx data."""

import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

from auxctmailer.xlsx_loader import XlsxTaskLoader
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


def load_competency_data(competencies_xlsx: str, logger: logging.Logger) -> dict:
    """Load competency data from Unit Summary xlsx.

    Returns:
        Dict mapping member_id -> list of competency dicts with:
            - competency_type, status, status_date
    """
    import pandas as pd
    import re

    members = {}
    if not competencies_xlsx or not Path(competencies_xlsx).exists():
        return members

    try:
        # Read xlsx and find header row
        df_raw = pd.read_excel(competencies_xlsx, header=None)

        # Find header row containing 'Original Certification Date'
        header_row = None
        for idx in range(min(30, len(df_raw))):
            row_values = df_raw.iloc[idx].astype(str).tolist()
            for val in row_values:
                if 'Original Certification' in val or 'Certification Date' in val:
                    header_row = idx
                    break
            if header_row is not None:
                break

        if header_row is None:
            logger.warning("Could not find header row in competencies xlsx")
            return members

        # Re-read with correct header
        df = pd.read_excel(competencies_xlsx, header=header_row)
        df.columns = [re.sub(r'\s*[↑↓]\s*', '', str(col)).strip() for col in df.columns]

        # Find the relevant columns
        unit_member_col = None
        for col in df.columns:
            if 'Unit/Member' in col:
                unit_member_col = col
                break

        cert_date_col = None
        for col in df.columns:
            if 'Original Certification' in col or 'Certification Date' in col:
                cert_date_col = col
                break

        if not unit_member_col or not cert_date_col:
            logger.warning("Missing required columns in competencies xlsx")
            return members

        # Parse the data
        current_member_id = None
        for idx, row in df.iterrows():
            # Check for new member
            unit_member = str(row.get(unit_member_col, ''))
            if 'Unit:' in unit_member:
                # Extract member ID
                match = re.search(r'(\d{7})$', unit_member)
                if match:
                    current_member_id = match.group(1)
                    if current_member_id not in members:
                        members[current_member_id] = []

            if current_member_id is None:
                continue

            # Skip subtotal rows and invalid entries
            comp_type = row.get('Competency Type')
            if pd.isna(comp_type):
                continue
            comp_type = str(comp_type).strip()
            # Skip if empty, subtotal, count, or just a number
            if comp_type.lower() in ['subtotal', 'count', ''] or comp_type.isdigit():
                continue
            status = row.get('Status', '')
            cert_date = row.get(cert_date_col)

            # Format date
            date_str = None
            if pd.notna(cert_date):
                if isinstance(cert_date, str):
                    date_str = cert_date
                else:
                    try:
                        date_str = pd.to_datetime(cert_date).strftime('%m/%d/%Y')
                    except:
                        date_str = str(cert_date)

            members[current_member_id].append({
                'competency_type': comp_type,
                'competency_status': str(status) if pd.notna(status) else 'Unknown',
                'status_date': date_str,
            })

        total_comps = sum(len(v) for v in members.values())
        logger.info(f"Loaded {total_comps} competencies for {len(members)} members")

    except Exception as e:
        logger.warning(f"Could not load competency data: {e}")

    return members


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
    competency_data = load_competency_data(args.competencies_xlsx, logger) if args.competencies_xlsx else {}

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
            all_comps = competency_data[member.member_id]
            task_comps = {c['competency_type']: c for c in ctx.get('competencies', [])}

            # Build merged competencies list with proper sorting
            merged = []
            for comp_info in all_comps:
                comp_type = comp_info['competency_type']
                if comp_type in task_comps:
                    # Competency has tasks - use task data but add status_date
                    merged_comp = task_comps[comp_type].copy()
                    merged_comp['status_date'] = comp_info['status_date']
                else:
                    # Competency has no tasks - create entry from Unit Summary
                    status = comp_info['competency_status']
                    status_lower = status.lower() if status else ''
                    if 'trainee' in status_lower or 'not certified' in status_lower:
                        status_bucket = 'trainee'
                    elif 'reyr' in status_lower or 'rewk' in status_lower:
                        status_bucket = 'lapsed'
                    else:
                        status_bucket = 'certified'

                    is_auxct = 'AUXCT' in comp_type.upper() or 'CORE TRAINING' in comp_type.upper()

                    merged_comp = {
                        'competency_type': comp_type,
                        'competency_status': status,
                        'status_bucket': status_bucket,
                        'status_date': comp_info['status_date'],
                        'is_auxct': is_auxct,
                        'is_lapsed': status_bucket == 'lapsed',
                        'overall_urgency': 'green',  # No tasks = green
                        'tasks': [],
                        'tasks_red': [],
                        'tasks_yellow': [],
                        'tasks_green': [],
                        'has_red': False,
                        'has_yellow': False,
                        'has_green': False,
                    }
                merged.append(merged_comp)

            # Sort: AUXCT first, then by status bucket, then alphabetically
            def sort_key(c):
                is_auxct = 0 if c.get('is_auxct') else 1
                bucket_order = {'trainee': 1, 'certified': 2, 'lapsed': 3}
                status_order = bucket_order.get(c.get('status_bucket', 'certified'), 99)
                return (is_auxct, status_order, c['competency_type'].upper())

            merged.sort(key=sort_key)
            ctx['competencies'] = merged

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
                filename = f"{member_num}_{first_name}_{last_name}.html".replace(' ', '_')
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
            filename = f"{member_num}_{first_name}_{last_name}.html".replace(' ', '_')
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
