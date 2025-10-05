# Automated Retry Workflow for SendGrid Failures

## Overview

When SendGrid delivery failures occur (bounces, blocks, DNSBL issues), you can automatically retry those emails via SMTP using `retry_failed_emails.py`.

## Why This Happens

SendGrid uses shared IP addresses that may occasionally be listed on DNSBLs (DNS-based blacklists), causing email providers like Comcast to block deliveries. Using your own SMTP server (Gmail) bypasses this issue.

## Quick Start

**Two ways to run the retry script:**

### Option A: Using wrapper script (easiest)
```bash
./run_retry.sh --list-only --html-dir "sent_emails_YYYY-MM-DD"
```

### Option B: Activate venv manually
```bash
source venv/bin/activate
python retry_failed_emails.py --list-only --html-dir "sent_emails_YYYY-MM-DD"
```

Both methods work the same - the wrapper script just activates the virtual environment for you.

## Workflow Options

### Option 1: Check for Failures Only (List Mode)

Query SendGrid API and list failures without attempting any retry:

```bash
# Just list what failed - no SMTP retry attempt
./run_retry.sh \
  --html-dir "sent_emails_YYYY-MM-DD" \
  --csv-file MemberEmail.csv \
  --list-only
```

**Use this when:**
- You want to see if there are any failures
- You're diagnosing SendGrid issues
- You want to review failures before retrying

### Option 2: Fully Automated Retry (Recommended)

Query SendGrid API, find matching HTML files, and retry via SMTP in one command:

```bash
# Dry run first (recommended)
./run_retry.sh \
  --html-dir "sent_emails_YYYY-MM-DD" \
  --csv-file MemberEmail.csv \
  --dry-run

# Production run
./run_retry.sh \
  --html-dir "sent_emails_YYYY-MM-DD" \
  --csv-file MemberEmail.csv
```

### Option 3: Manual Selection

If you've already organized failed deliveries into a subdirectory:

```bash
# Retry specific subdirectory
./run_retry.sh \
  --html-dir "sent_emails_YYYY-MM-DD/Delivery Failures" \
  --csv-file MemberEmail.csv
```

### Option 4: Time-Based Filtering

Only retry failures that occurred after a specific time:

```bash
# Get Unix timestamp for a specific date/time
# Example: October 5, 2025 at 8:00 AM
# Use: date -j -f "%Y-%m-%d %H:%M:%S" "2025-10-05 08:00:00" +%s
# Returns: 1728129600

./run_retry.sh \
  --html-dir "sent_emails_YYYY-MM-DD" \
  --csv-file MemberEmail.csv \
  --start-time 1728129600
```

## What the Script Does

1. **Queries SendGrid API** for:
   - Bounces (email server rejected the message)
   - Blocks (IP/content-related issues)
   - Invalid emails (non-existent addresses)

2. **Finds matching HTML files** from your sent emails archive

3. **Re-sends via SMTP** using credentials from `.env` (unless `--list-only` is used)

## Understanding the Modes

### `--list-only` (Query Only)
- ✅ Queries SendGrid API
- ✅ Shows all failures with details
- ✅ Matches HTML files
- ❌ Does NOT attempt SMTP retry
- **Use:** To check if there are failures without taking action

### `--dry-run` (Simulation)
- ✅ Queries SendGrid API
- ✅ Shows all failures with details
- ✅ Matches HTML files
- ✅ Simulates SMTP retry (shows what would be sent)
- ❌ Does NOT actually send emails
- **Use:** To verify everything before production run

### Production Mode (No Flags)
- ✅ Queries SendGrid API
- ✅ Shows all failures with details
- ✅ Matches HTML files
- ✅ Actually sends emails via SMTP
- **Use:** To retry failed deliveries

## Example Output

```
Querying SendGrid for delivery failures...
--------------------------------------------------------------------------------
Checking bounces...
  - john@example.com: 550 Mailbox not found (1759663916)
  Found 1 bounces
Checking blocks...
  - mary@comcast.net: 554 IP found on DNSBL (1759663917)
  Found 1 blocks
Checking invalid_emails...
  Found 0 invalid_emails
--------------------------------------------------------------------------------
Total unique failed emails: 2

Scanning 53 HTML files in sent_emails_2025-10-05...
  ✓ Found: 1234567_JOHN_DOE.html → john@example.com
  ✓ Found: 7654321_MARY_SMITH.html → mary@comcast.net

Found 2 HTML files to retry

SMTP Configuration:
  Host: smtp.gmail.com:587
  TLS: True
  User: pgaffney2000@gmail.com
  From: paul@gaffney.io

Starting SMTP retry sends...

--------------------------------------------------------------------------------
Sending to John Doe (john@example.com)...
  ✅ SUCCESS
--------------------------------------------------------------------------------
Sending to Mary Smith (mary@comcast.net)...
  ✅ SUCCESS
--------------------------------------------------------------------------------

================================================================================
RETRY SUMMARY:
  Total files processed: 2
  ✅ Successfully sent: 2
  ❌ Failed: 0
================================================================================
```

## Requirements

- `.env` file with SMTP configuration (SMTP_USER, SMTP_PASSWORD)
- SendGrid API key in `.env` (for querying failures)
- HTML archive directory from previous send
- MemberEmail.csv for email address lookups

## Common Failure Types

### DNSBL Blocks (Comcast/Others)
```
554 IP found on one or more DNSBLs
```
**Solution:** Retry via SMTP (your Gmail account has better reputation)

### Bounces
```
550 Mailbox not found
```
**Solution:** Verify email address is correct, may need manual follow-up

### Invalid Emails
```
Email address does not exist
```
**Solution:** Update member email in your records

## Tips

1. **Always dry-run first** to verify what will be sent
2. **Check SendGrid Activity Feed** in the dashboard to confirm failures
3. **Archive HTML files** from every production run (`--save-html` option)
4. **Use time filtering** if you only want recent failures
5. **Monitor SMTP sending limits** (Gmail: 500/day for standard accounts)

## Troubleshooting

### "No failed emails found"
- Check SendGrid dashboard to confirm there were failures
- Verify SENDGRID_API_KEY is correct in `.env`
- Use `--start-time` if failures are older

### "No matching HTML files found"
- Verify HTML directory path is correct
- Check that HTML filenames match format: `MEMBERID_FIRST_LAST.html`
- Ensure Member IDs in filenames exist in MemberEmail.csv

### "SMTP authentication failed"
- Verify SMTP_USER and SMTP_PASSWORD in `.env`
- For Gmail, ensure you're using an app-specific password
- Check SMTP_HOST and SMTP_PORT are correct

## Related Scripts

- `send_backup_emails.py` - Manual retry from specific HTML directory
- `test_smtp_config.py` - Test SMTP configuration
- `auxctmailer/main.py` - Main email sending system
