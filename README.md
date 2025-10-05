# AUXCTMailer

Email automation system for sending custom emails to AUXCT members based on database records.

## Features

- Load member records from CSV files with automatic joining on Member ID
- Filter members by any column criteria
- Send personalized emails using Jinja2 templates
- Bulk email sending with success/failure tracking
- Course deadline tracking with overdue and due-soon warnings
- Uniform inspection status tracking with exemption support
- Extraction date support for accurate due date calculations
- Special handling for specific courses (Suicide Prevention, Civil Rights, SAPRR)
- HTML archiving of sent emails (important for SendGrid free tier)
- Dry-run mode to preview emails before sending
- SendGrid and SMTP email provider support

## Installation

1. Navigate to the project directory:
   ```bash
   cd ~/Projects/AUXCTMailer
   ```

2. Create and activate virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the package:
   ```bash
   pip install -e .
   ```

## Configuration

Create a `.env` file in the project root with your email provider settings.

### Option 1: SendGrid (Recommended)

SendGrid is more reliable for bulk emails and has better deliverability.

1. Sign up for a [SendGrid account](https://sendgrid.com/) (free tier available)
2. Create an API key in SendGrid dashboard
3. Configure `.env`:

```env
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=your-sendgrid-api-key-here
FROM_EMAIL=auxct@example.com
```

### Option 2: SMTP

For traditional SMTP servers (Gmail, etc.):

```env
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=auxct@example.com
```

**Note**: For Gmail, you must create an [App Password](https://support.google.com/accounts/answer/185833) instead of using your regular password.

## Usage

### Basic Usage

Send emails to all members with course warnings and HTML archiving:

```bash
python -m auxctmailer.main \
  --training-csv "2025-10-01 AUX-CT DB.csv" \
  --email-csv MemberEmail.csv \
  --courses-csv "AUX-CT courses.csv" \
  --extraction-date "10/01/2025" \
  --template training_reminder.html \
  --subject "AUXCT Training Reminder - {{ first_name }} {{ last_name }}" \
  --save-html sent_emails_2025-10-05
```

### Test Email (Send to Yourself)

Test the email by sending to a single member (yourself):

```bash
python -m auxctmailer.main \
  --training-csv "2025-10-01 AUX-CT DB.csv" \
  --email-csv MemberEmail.csv \
  --courses-csv "AUX-CT courses.csv" \
  --extraction-date "10/01/2025" \
  --template training_reminder.html \
  --subject "AUXCT Training Reminder - {{ first_name }} {{ last_name }}" \
  --filter "Member #=5008388" \
  --save-html test_emails
```

### Dry Run

Preview what would be sent without actually sending emails:

```bash
python -m auxctmailer.main \
  --training-csv "2025-10-01 AUX-CT DB.csv" \
  --email-csv MemberEmail.csv \
  --courses-csv "AUX-CT courses.csv" \
  --extraction-date "10/01/2025" \
  --template training_reminder.html \
  --subject "AUXCT Training Reminder - {{ first_name }} {{ last_name }}" \
  --dry-run
```

### Filter Examples

Send only to certified members:
```bash
--filter Status=Certified
```

Send to a specific member:
```bash
--filter "Member #=1244671"
```

Multiple filter criteria:
```bash
--filter Status=Certified "Uniform Exempt=0"
```

### Command Line Options

- `--training-csv PATH` - Path to CSV file with training/competency records (required)
- `--email-csv PATH` - Path to CSV file with member emails (required)
- `--courses-csv PATH` - Path to CSV file with course information and enrollment keys (optional but recommended)
- `--extraction-date DATE` - Date when training data was extracted in MM/DD/YYYY format (optional, defaults to today)
- `--template NAME` - Email template filename in `auxctmailer/templates/` (required)
- `--subject TEXT` - Email subject line, can use Jinja2 variables like `{{ first_name }}` (required)
- `--filter KEY=VALUE` - Filter members by column values (optional, multiple allowed)
- `--save-html DIR` - Directory to save HTML copies of sent emails (optional but strongly recommended)
- `--dry-run` - Preview emails without sending (optional)
- `--template-dir PATH` - Custom templates directory (optional)

## CSV Format

The system uses three CSV files:

### Training CSV (`2025-10-01 AUX-CT DB.csv`)
Contains member training and competency data with columns:
- `Member #` - Member identifier (used for joining)
- `First Name`, `Last Name` - Member name
- `Status` - Certification status (e.g., "Certified", "REYR")
- `Uniform Inspection` - Date of last uniform inspection
- Course columns: `PAWR_810015`, `POSH_810000`, `SETA_810030`, `SP_100643`, `SAPRR_502379`, `CRA_502319`
  - Values represent days until due **from the extraction date** (not from today)

### Email CSV (`MemberEmail.csv`)
Contains member contact information:
- `Member ID` - Member identifier (used for joining with Training CSV)
- `First Name`, `Last Name` - Member name
- `Email` - Email address
- `Uniform Exempt` - 0 (not exempt) or 1 (exempt from uniform inspections)

### Courses CSV (`AUX-CT courses.csv`)
Contains course details for generating warning messages:
- `Code` - Course code matching column names in Training CSV (e.g., `PAWR_810015`)
- `Title` - Friendly course name (e.g., "Personal and Water Safety")
- `URL` - Direct link to course enrollment page
- `EnrollmentCode` - Moodle enrollment key for the course

The Training and Email files are automatically joined on `Member #` / `Member ID`.

## Important Concepts

### Extraction Date Logic

The training data CSV is a snapshot from a specific date (the "extraction date"). Course due dates are calculated FROM that extraction date, not from today.

**How it works:**
1. Training CSV shows "days until due" from the extraction date
2. System calculates: `actual_due_date = extraction_date + days_until_due`
3. System then calculates: `days_from_today = actual_due_date - today`
4. This ensures accurate warnings as time passes after the data export

**Example:**
- Extraction date: 10/01/2025
- Course shows: 180 days until due
- Actual due date: 10/01/2025 + 180 days = 03/30/2026
- If today is 10/05/2025: Email shows "176 days until due"

### Special Course Handling

Three courses with `DaysDue=0` receive special treatment (shown as yellow warning due 12/31 of current year):
- `SP_100643` - Suicide Prevention
- `CRA_502319` - Civil Rights Awareness
- `SAPRR_502379` - Sexual Assault Prevention, Response, and Recovery

These are annual requirements that should be completed by year-end.

### Uniform Inspection Logic

- If `Uniform Exempt = 1`: No inspection warning shown
- If last inspection is before 1/1/current_year: Warning shown
- If last inspection is current year or later: No warning shown

### Course Warning Categories

- **No warning:** Courses due more than 365 days from today
- **Yellow "due soon":** Courses due within next 365 days
- **Red "overdue":** Courses with due dates in the past

## Email Templates

Create HTML email templates in `auxctmailer/templates/` using Jinja2 syntax.

### Available Template Variables

**Member Information:**
- `{{ first_name }}` - Auto-converted to title case (PAUL → Paul)
- `{{ last_name }}` - Member's last name
- `{{ member_num }}` - Member number
- `{{ status }}` - Certification status (Certified, REYR, etc.)
- `{{ extraction_date }}` - Date when training data was extracted
- `{{ extraction_plus_365 }}` - Date 365 days after extraction

**Uniform Inspection:**
- `{{ uniform_inspection }}` - Date of last inspection (or None)
- `{{ uniform_exempt }}` - Boolean, true if member is exempt
- `{{ needs_uniform_inspection }}` - Boolean, true if inspection needed this year

**Course Warnings:**
- `{{ has_overdue_courses }}` - Boolean, true if any courses are overdue
- `{{ has_due_soon_courses }}` - Boolean, true if any courses due within 365 days
- `{{ courses_overdue }}` - List of overdue courses, each with:
  - `title` - Course name
  - `url` - Enrollment URL
  - `enrollment_code` - Moodle enrollment key
  - `days_overdue` - Number of days past due
- `{{ courses_due_soon }}` - List of upcoming courses, each with:
  - `title` - Course name
  - `url` - Enrollment URL
  - `enrollment_code` - Moodle enrollment key
  - `days_until_due` - Days until due date
  - `due_date` - Formatted due date (MM/DD/YYYY)

**General:**
- `{{ current_year }}` - Current year (e.g., 2025)
- `{{ current_year_start }}` - 1/1/current_year
- `{{ current_year_end }}` - 12/31/current_year

**Note:** All CSV columns are available as template variables. Column names with spaces or special characters are automatically normalized (e.g., `First Name` becomes `first_name`, `Member #` becomes `member_num`).

## Project Structure

```
AUXCTMailer/
├── auxctmailer/
│   ├── __init__.py
│   ├── database.py      # CSV database operations
│   ├── mailer.py        # Email sending and templating
│   ├── main.py          # CLI entry point
│   └── templates/       # Email templates directory
├── venv/                # Virtual environment
├── .env                 # SMTP configuration (not in git)
├── .gitignore
├── README.md
├── requirements.txt
└── setup.py
```

## Development

### Running from source

```bash
python -m auxctmailer.main --csv test.csv --template test.html --subject "Test"
```

### Adding dependencies

Add to `requirements.txt` and `setup.py`, then:

```bash
pip install -e .
```

## HTML Email Archiving

The `--save-html` option creates a local archive of all sent emails. This is **highly recommended** for several reasons:

1. **SendGrid Free Tier:** SendGrid's free tier doesn't store sent email history
2. **Audit Trail:** Maintain a record of exactly what was sent to each member
3. **Troubleshooting:** Reference archived emails if members have questions
4. **Compliance:** Keep records for organizational requirements

**File naming:** `{member_num}_{first_name}_{last_name}.html`

**Example:** `5008388_Paul_GAFFNEY.html`

**Recommendation:** Create dated directories like `sent_emails_2025-10-05` and compress for long-term storage:
```bash
tar -czf sent_emails_2025-10-05.tar.gz sent_emails_2025-10-05/
```

## Security Notes

- Never commit `.env` files or CSV files with real member data
- Use app-specific passwords for Gmail (not your main password)
- CSV files and HTML archives are excluded from git via `.gitignore`
- Consider encrypting sensitive member data at rest
- HTML archives contain member information - store securely

## Example Workflow

1. Export training data from AUXDATA to `YYYY-MM-DD AUX-CT DB.csv`
2. Update member emails in `MemberEmail.csv` (include Uniform Exempt column)
3. Verify courses in `AUX-CT courses.csv` (enrollment keys current)
4. Test with dry-run to verify count and preview email
5. Send test email to yourself using `--filter "Member #=YOUR_ID"`
6. Create archive directory: `mkdir sent_emails_$(date +%Y-%m-%d)`
7. Send to all with `--save-html sent_emails_$(date +%Y-%m-%d)`
8. Verify success count and check for failures
9. Archive HTML files for records
