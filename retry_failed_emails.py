#!/usr/bin/env python3
"""
Automated retry script for SendGrid delivery failures.

This script:
1. Queries SendGrid API for bounces, blocks, and invalid emails
2. Finds matching HTML files in the sent emails archive directory
3. Re-sends failed emails via SMTP

Configuration is loaded from .env file.
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Set
from dotenv import load_dotenv
import requests
import argparse

# Load environment variables
load_dotenv()

# SendGrid configuration
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
SENDGRID_API_BASE = "https://api.sendgrid.com/v3"

# SMTP configuration
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'true').lower() in ('true', '1', 'yes')
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
FROM_ADDRESS = os.getenv('FROM_EMAIL', SMTP_USER)


def get_sendgrid_suppressions(suppression_type: str, start_time: int = None) -> List[Dict]:
    """
    Query SendGrid API for suppressions (bounces, blocks, invalid emails).

    Args:
        suppression_type: One of 'bounces', 'blocks', 'invalid_emails', 'spam_reports'
        start_time: Optional Unix timestamp to retrieve suppressions after this time

    Returns:
        List of suppression records with email addresses and details
    """
    if not SENDGRID_API_KEY:
        print("ERROR: SENDGRID_API_KEY not found in .env file")
        return []

    endpoint = f"{SENDGRID_API_BASE}/suppression/{suppression_type}"
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }

    params = {}
    if start_time:
        params['start_time'] = start_time

    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR querying SendGrid {suppression_type}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return []


def get_all_failed_emails(start_time: int = None) -> Set[str]:
    """
    Get all failed email addresses from SendGrid suppressions.

    Args:
        start_time: Optional Unix timestamp to retrieve failures after this time

    Returns:
        Set of email addresses that failed
    """
    failed_emails = set()

    print("Querying SendGrid for delivery failures...")
    print("-" * 80)

    # Query each suppression type
    for suppression_type in ['bounces', 'blocks', 'invalid_emails']:
        print(f"Checking {suppression_type}...")
        suppressions = get_sendgrid_suppressions(suppression_type, start_time)

        for record in suppressions:
            email = record.get('email')
            if email:
                failed_emails.add(email.lower())
                reason = record.get('reason', 'Unknown')
                created = record.get('created', 'Unknown time')
                print(f"  - {email}: {reason} ({created})")

        print(f"  Found {len(suppressions)} {suppression_type}")

    print("-" * 80)
    print(f"Total unique failed emails: {len(failed_emails)}\n")

    return failed_emails


def find_html_files_for_emails(html_dir: str, failed_emails: Set[str], csv_file: str) -> List[Path]:
    """
    Find HTML files that correspond to failed email addresses.

    Args:
        html_dir: Directory containing sent email HTML files
        failed_emails: Set of email addresses that failed
        csv_file: Path to MemberEmail.csv for email lookups

    Returns:
        List of HTML file paths to retry
    """
    import csv
    import re

    # Load member emails from CSV
    member_emails = {}
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                member_id = row['Member ID']
                member_emails[member_id] = row['Email'].lower()
    except Exception as e:
        print(f"ERROR loading member emails from CSV: {e}")
        return []

    # Find HTML files matching failed emails
    html_path = Path(html_dir)
    if not html_path.exists():
        print(f"ERROR: HTML directory not found: {html_dir}")
        return []

    html_files = list(html_path.glob("*.html"))
    retry_files = []

    print(f"Scanning {len(html_files)} HTML files in {html_dir}...")

    for html_file in html_files:
        # Parse filename: 1234567_FIRST_LAST.html
        match = re.match(r'(\d+)_', html_file.name)
        if match:
            member_id = match.group(1)
            email = member_emails.get(member_id)

            if email and email in failed_emails:
                retry_files.append(html_file)
                print(f"  ✓ Found: {html_file.name} → {email}")

    print(f"\nFound {len(retry_files)} HTML files to retry\n")
    return retry_files


def retry_via_smtp(html_files: List[Path], csv_file: str, dry_run: bool = False):
    """
    Re-send failed emails via SMTP.

    Args:
        html_files: List of HTML file paths to send
        csv_file: Path to MemberEmail.csv for email addresses
        dry_run: If True, don't actually send emails
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    import csv
    import re

    if not SMTP_USER or not SMTP_PASSWORD:
        print("ERROR: SMTP configuration missing in .env file")
        return

    print(f"SMTP Configuration:")
    print(f"  Host: {SMTP_HOST}:{SMTP_PORT}")
    print(f"  TLS: {SMTP_USE_TLS}")
    print(f"  User: {SMTP_USER}")
    print(f"  From: {FROM_ADDRESS}\n")

    if dry_run:
        print("=== DRY RUN MODE - No emails will be sent ===\n")

    # Load member data
    members = {}
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            member_id = row['Member ID']
            members[member_id] = {
                'email': row['Email'],
                'first_name': row['First Name'],
                'last_name': row['Last Name']
            }

    success_count = 0
    failure_count = 0

    print("Starting SMTP retry sends...\n")
    print("-" * 80)

    for html_file in html_files:
        # Parse filename
        match = re.match(r'(\d+)_([A-Z]+)_([A-Z]+)\.html', html_file.name)
        if not match:
            print(f"❌ SKIP: Could not parse filename: {html_file.name}")
            failure_count += 1
            continue

        member_id = match.group(1)

        if member_id not in members:
            print(f"❌ SKIP: Member ID {member_id} not found in CSV")
            failure_count += 1
            continue

        member = members[member_id]
        recipient_email = member['email']
        first_name = member['first_name'].title()
        last_name = member['last_name'].title()
        subject = f"AUXCT Training Reminder - {first_name} {last_name}"

        # Read HTML content
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        print(f"Sending to {first_name} {last_name} ({recipient_email})...")

        if dry_run:
            print(f"  [DRY RUN] Would send via SMTP")
            success_count += 1
        else:
            # Send email via SMTP
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = FROM_ADDRESS
                msg['To'] = recipient_email
                msg['Reply-To'] = FROM_ADDRESS
                msg.attach(MIMEText(html_content, 'html'))

                if SMTP_USE_TLS:
                    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
                    server.starttls()
                else:
                    if SMTP_PORT == 465:
                        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
                    else:
                        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)

                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
                server.quit()

                print(f"  ✅ SUCCESS")
                success_count += 1
            except Exception as e:
                print(f"  ❌ FAILED: {e}")
                failure_count += 1

        print("-" * 80)

    # Summary
    print(f"\n{'=' * 80}")
    print(f"RETRY SUMMARY:")
    print(f"  Total files processed: {len(html_files)}")
    print(f"  ✅ Successfully sent: {success_count}")
    print(f"  ❌ Failed: {failure_count}")
    print(f"{'=' * 80}")


def main():
    parser = argparse.ArgumentParser(
        description='Automatically retry SendGrid delivery failures via SMTP'
    )
    parser.add_argument(
        '--html-dir',
        required=True,
        help='Directory containing sent email HTML files'
    )
    parser.add_argument(
        '--csv-file',
        default='./MemberEmail.csv',
        help='Path to MemberEmail.csv (default: ./MemberEmail.csv)'
    )
    parser.add_argument(
        '--start-time',
        type=int,
        help='Unix timestamp to retrieve failures after this time (optional)'
    )
    parser.add_argument(
        '--list-only',
        action='store_true',
        help='Only query SendGrid and list failures without attempting SMTP retry'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be sent without actually sending (implies --list-only behavior plus retry simulation)'
    )

    args = parser.parse_args()

    # Step 1: Query SendGrid for failures
    failed_emails = get_all_failed_emails(args.start_time)

    if not failed_emails:
        print("No failed emails found in SendGrid suppressions.")
        return 0

    # Step 2: Find matching HTML files
    html_files = find_html_files_for_emails(args.html_dir, failed_emails, args.csv_file)

    if not html_files:
        print("No matching HTML files found to retry.")
        return 0

    # Step 3: If list-only mode, print summary and exit
    if args.list_only:
        print("\n" + "=" * 80)
        print("LIST-ONLY MODE - No retry will be attempted")
        print("=" * 80)
        print(f"\nSummary:")
        print(f"  Failed emails in SendGrid: {len(failed_emails)}")
        print(f"  Matching HTML files found: {len(html_files)}")
        print(f"\nTo retry these emails via SMTP, run without --list-only flag")
        print("=" * 80)
        return 0

    # Step 4: Retry via SMTP
    retry_via_smtp(html_files, args.csv_file, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    exit(main())
