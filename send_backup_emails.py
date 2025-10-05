"""
Backup email sender for re-sending failed emails from archived HTML files.

This script reads HTML files from a directory (e.g., SendGrid delivery failures),
matches them to member emails from CSV, and re-sends them via SMTP.

SMTP credentials are loaded from .env file.
"""
import smtplib
import csv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
HTML_FOLDER = "./sent_emails_2025-10-05/Delivery Failures"  # Update this path to your folder
CSV_FILE = "./MemberEmail.csv"

# Email configuration from .env
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'true').lower() in ('true', '1', 'yes')
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
FROM_ADDRESS = os.getenv('FROM_EMAIL', SMTP_USER)

def load_member_emails(csv_path):
    """Load member emails from CSV into a dictionary keyed by member ID"""
    members = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            member_id = row['Member ID']
            members[member_id] = {
                'email': row['Email'],
                'first_name': row['First Name'],
                'last_name': row['Last Name']
            }
    return members

def parse_filename(filename):
    """Extract member ID, first name, and last name from filename"""
    # Format: 1143581_MARILYN_FARREN.html
    match = re.match(r'(\d+)_([A-Z]+)_([A-Z]+)\.html', filename)
    if match:
        return {
            'member_id': match.group(1),
            'first_name': match.group(2),
            'last_name': match.group(3)
        }
    return None

def send_email(recipient_email, subject, html_content):
    """Send an email via SMTP using configuration from .env"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = FROM_ADDRESS
    msg['To'] = recipient_email
    msg['Reply-To'] = FROM_ADDRESS

    # Attach HTML content
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)

    # Send via SMTP
    try:
        if SMTP_USE_TLS:
            # Use STARTTLS (port 587)
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
        else:
            # Use SSL (port 465) or unencrypted (port 25)
            if SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
            else:
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)

        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "Success"
    except Exception as e:
        return False, str(e)

def main():
    # Validate SMTP configuration
    if not SMTP_USER or not SMTP_PASSWORD:
        print("ERROR: SMTP configuration missing in .env file")
        print("Required: SMTP_USER, SMTP_PASSWORD")
        print("Optional: SMTP_HOST (default: smtp.gmail.com), SMTP_PORT (default: 587)")
        print("Optional: SMTP_USE_TLS (default: true), FROM_EMAIL (default: SMTP_USER)")
        return 1

    print(f"SMTP Configuration:")
    print(f"  Host: {SMTP_HOST}:{SMTP_PORT}")
    print(f"  TLS: {SMTP_USE_TLS}")
    print(f"  User: {SMTP_USER}")
    print(f"  From: {FROM_ADDRESS}\n")

    # Load member data
    print("Loading member emails from CSV...")
    members = load_member_emails(CSV_FILE)
    print(f"Loaded {len(members)} members from CSV\n")
    
    # Get all HTML files in the folder
    html_folder = Path(HTML_FOLDER)
    html_files = list(html_folder.glob("*.html"))
    print(f"Found {len(html_files)} HTML files in {HTML_FOLDER}\n")
    
    if not html_files:
        print("ERROR: No HTML files found. Please check the HTML_FOLDER path.")
        return
    
    # Process each HTML file
    success_count = 0
    failure_count = 0
    
    print("Starting email sends...\n")
    print("-" * 80)
    
    for html_file in html_files:
        # Parse the filename
        file_info = parse_filename(html_file.name)
        if not file_info:
            print(f"❌ SKIP: Could not parse filename: {html_file.name}")
            failure_count += 1
            continue
        
        member_id = file_info['member_id']
        first_name = file_info['first_name']
        last_name = file_info['last_name']
        
        # Get member email from CSV
        if member_id not in members:
            print(f"❌ SKIP: Member ID {member_id} not found in CSV: {html_file.name}")
            failure_count += 1
            continue
        
        member = members[member_id]
        recipient_email = member['email']
        
        # Create subject line with proper capitalization
        csv_first = member['first_name'].title()
        csv_last = member['last_name'].title()
        subject = f"AUXCT Training Reminder - {csv_first} {csv_last}"
        
        # Read HTML content
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Send email
        print(f"Sending to {csv_first} {csv_last} ({recipient_email})...")
        success, message = send_email(recipient_email, subject, html_content)
        
        if success:
            print(f"✅ SUCCESS: Email sent to {recipient_email}")
            success_count += 1
        else:
            print(f"❌ FAILED: {recipient_email} - Error: {message}")
            failure_count += 1
        
        print("-" * 80)
    
    # Summary
    print(f"\n{'=' * 80}")
    print(f"SUMMARY:")
    print(f"  Total files processed: {len(html_files)}")
    print(f"  ✅ Successfully sent: {success_count}")
    print(f"  ❌ Failed: {failure_count}")
    print(f"{'=' * 80}")

    return 0 if failure_count == 0 else 1

if __name__ == "__main__":
    exit(main())
