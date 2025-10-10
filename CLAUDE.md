# AUXCTMailer Project Documentation

## Project Overview

AUXCTMailer is an email automation system for the U.S. Coast Guard Auxiliary. It sends personalized training reminder emails to members based on their AUXCT (AUX Core Training) status.

**Primary Use Case:** Send automated training reminders to flotilla members with personalized course deadlines, uniform inspection reminders, and contact information. Supports multiple units with dynamic unit name and number display.

## Key Features

- ✅ **Multi-unit support** - Dynamic unit name and number lookup from UnitDetails.csv
- ✅ **Pretty formatting** - Unit names (Title Case + "Flotilla" suffix) and numbers (DDD-VV-UU format)
- ✅ Personalized emails with member-specific training requirements
- ✅ Course deadline tracking with yellow (due soon) and red (overdue) warnings
- ✅ Uniform inspection status tracking with exemption support
- ✅ Special handling for specific courses (Suicide Prevention, Civil Rights Awareness, SAPRR)
- ✅ Extraction date support for accurate due date calculations
- ✅ SendGrid and SMTP email provider support
- ✅ HTML archiving of sent emails (important for SendGrid free tier)
- ✅ Dry-run mode for testing

## Project Structure

```
AUXCTMailer/
├── auxctmailer/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── database.py          # CSV data loading and member filtering
│   ├── mailer.py            # Email sending and template rendering
│   └── templates/
│       ├── training_reminder.html  # Main email template
│       └── example.html            # Sample template
├── .env                     # SendGrid credentials (NOT in Git)
├── .env.example            # Environment variable template
├── .gitignore
├── requirements.txt
├── setup.py
├── README.md
└── CLAUDE.md               # This file

# Data Files (NOT in Git):
├── 2025-10-01 AUX-CT DB.csv    # Training data export with Unit/Member/Competency/Status field
├── MemberEmail.csv              # Member emails + Uniform Exempt flag
├── AUX-CT courses.csv           # Course information with enrollment keys
└── UnitDetails.csv              # Unit names and details (optional for multi-unit support)
```

## Important Configuration

### Environment Variables (.env)

```bash
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.xxxxxxxxxx.yyyyyyyyyyyyyyyy
FROM_EMAIL=paul@gaffney.io
```

**Note:** The `.env` file is in `.gitignore` and contains sensitive credentials.

### SendGrid Configuration

- **Provider:** SendGrid
- **Tier:** Free (100 emails/day limit)
- **From Email:** paul@gaffney.io (must be verified in SendGrid)
- **API Key:** Stored in `.env` file

### Data Files

1. **Training CSV:** `2025-10-01 AUX-CT DB.csv`
   - Contains member training records
   - Key columns: Member #, First Name, Last Name, Status, Uniform Inspection, Unit/Member/Competency/Status
   - Course columns: PAWR_810015, POSH_810000, SETA_810030, SP_100643, SAPRR_502379, CRA_502319
   - Values in course columns = days until due from extraction date
   - Unit/Member/Competency/Status format: `Unit: 0131102 | LASTNAME. FIRSTNAME 1234567 | AUXCT - CORE TRAINING (Status)`

2. **Email CSV:** `MemberEmail.csv`
   - Contains: Member ID, Last Name, First Name, Email, Uniform Exempt
   - Uniform Exempt: 0 = not exempt, 1 = exempt from inspections

3. **Courses CSV:** `AUX-CT courses.csv`
   - Contains: Code, Title, URL, EnrollmentCode
   - Maps course codes to friendly names and Moodle enrollment keys

4. **Units CSV:** `UnitDetails.csv` (optional)
   - Contains: Unit Number, Unit Name, Type, Last Modified Date, FSO-IS, FSO-MT
   - Used for dynamic unit name lookup
   - Unit Number format: 7 digits (DDDVVUU - District/Division/Unit)
   - Unit names are auto-prettified: "WOODS HOLE FLOTILLA" → "Woods Hole Flotilla"

### Extraction Date Logic

**Critical Concept:** Training data has a snapshot date (extraction date). Course "days until due" are calculated FROM that date, not from today.

- Extraction Date: `10/01/2025` (for current data)
- Course column value: Days until due FROM extraction date
- Email shows: Days until due FROM today
- Calculation: `actual_due_date = extraction_date + days_until_due`, then `days_from_today = actual_due_date - today`

### Special Course Handling

Three courses with `DaysDue=0` get special treatment (yellow warning with 12/31/current_year due date):
- `SP_100643` - Suicide Prevention
- `CRA_502319` - Civil Rights Awareness
- `SAPRR_502379` - Sexual Assault Prevention, Response, and Recovery

## Common Commands

### Setup (One-Time)

```bash
cd ~/Projects/AUXCTMailer
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Daily Use

```bash
cd ~/Projects/AUXCTMailer
source venv/bin/activate
```

### Test Email (Send to yourself)

```bash
python -m auxctmailer.main \
  --training-csv "2025-10-01 AUX-CT DB.csv" \
  --email-csv MemberEmail.csv \
  --courses-csv "AUX-CT courses.csv" \
  --units-csv UnitDetails.csv \
  --extraction-date "10/01/2025" \
  --template training_reminder.html \
  --subject "AUXCT Training Reminder - {{ first_name }} {{ last_name }}" \
  --filter "Member #=5008388" \
  --save-html test_emails
```

### Dry Run (Preview without sending)

```bash
python -m auxctmailer.main \
  --training-csv "2025-10-01 AUX-CT DB.csv" \
  --email-csv MemberEmail.csv \
  --courses-csv "AUX-CT courses.csv" \
  --units-csv UnitDetails.csv \
  --extraction-date "10/01/2025" \
  --template training_reminder.html \
  --subject "AUXCT Training Reminder - {{ first_name }} {{ last_name }}" \
  --dry-run
```

### Production Run (Send to all members)

```bash
python -m auxctmailer.main \
  --training-csv "2025-10-01 AUX-CT DB.csv" \
  --email-csv MemberEmail.csv \
  --courses-csv "AUX-CT courses.csv" \
  --units-csv UnitDetails.csv \
  --extraction-date "10/01/2025" \
  --template training_reminder.html \
  --subject "AUXCT Training Reminder - {{ first_name }} {{ last_name }}" \
  --save-html sent_emails_YYYY-MM-DD
```

**Important:** Always use `--save-html` to archive sent emails!

### Filter Options

Filter by specific member:
```bash
--filter "Member #=1244671"
```

Filter by status:
```bash
--filter Status=Certified
```

Multiple filters:
```bash
--filter Status=Certified "Uniform Exempt=0"
```

## Email Template Personalization

The template uses Jinja2 syntax with these key variables:

### Member Information
- `{{ first_name }}` - Auto-converted to title case (PAUL → Paul)
- `{{ last_name }}`
- `{{ member_num }}`
- `{{ status }}` - Certified, REYR, etc.
- `{{ uniform_inspection }}` - Date of last inspection
- `{{ uniform_exempt }}` - Boolean, true if exempt
- `{{ extraction_date }}` - Date training data was extracted
- `{{ extraction_plus_365 }}` - Date 365 days after extraction
- `{{ unit_number }}` - Raw unit number (e.g., "0131102")
- `{{ unit_number_pretty }}` - Formatted unit number (e.g., "013-11-02")
- `{{ unit_name }}` - Raw unit name (e.g., "WOODS HOLE FLOTILLA")
- `{{ unit_name_pretty }}` - Formatted unit name (e.g., "Woods Hole Flotilla")

### Course Warnings
- `{% if has_overdue_courses %}` - Red warning section
- `{% if has_due_soon_courses %}` - Yellow warning section
- `{{ courses_overdue }}` - List with: title, url, enrollment_code, days_overdue
- `{{ courses_due_soon }}` - List with: title, url, enrollment_code, days_until_due, due_date

### Contact Information (hardcoded in template)
- IS Officer: Paul Gaffney, FSO-IS
- Email: paul.gaffney@hey.com
- Phone/Text: 508-904-1393

## Data Processing Logic

### Uniform Inspection
- If `Uniform Exempt = 1`: No inspection warning
- If last inspection before 1/1/current_year: Show warning
- If last inspection is current year: No warning

### Course Warnings
- `days_from_today > 365`: No warning
- `0 < days_from_today <= 365`: Yellow "due soon" warning
- `days_from_today < 0`: Red "overdue" warning
- **Exception:** SP_100643, CRA_502319, SAPRR_502379 with DaysDue=0 → Yellow warning due 12/31

### Status-Based Messages
- **Certified + no courses due:** Green box with "no courses due prior to {extraction_date + 365 days}"
- **Certified + courses due:** Green box without extra message
- **REYR or other:** Yellow box with "Action Required"

## HTML Archive Files

Format: `{member_num}_{first_name}_{last_name}.html`

Examples:
- `5008388_Paul_GAFFNEY.html`
- `1244671_Ronald_GROSSMAN.html`

**Why:** SendGrid free tier doesn't store sent emails, so these provide a local record of exactly what was sent to each member.

## Troubleshooting

### SendGrid 401 Unauthorized
- Check API key in `.env` file
- Verify API key format starts with `SG.`
- Ensure API key has "Mail Send" permissions

### Missing Members
- Verify CSV files are in project root
- Check Member # matches between training and email CSVs
- Ensure email addresses are present in MemberEmail.csv

### Wrong Due Dates
- Verify `--extraction-date` parameter matches when training data was exported
- Check calculation: extraction_date + DaysDue = actual due date

### Template Errors
- Check Jinja2 syntax in `auxctmailer/templates/training_reminder.html`
- Verify all variable names match normalized context (underscores, not spaces)

## Git Repository

**Remote:** https://github.com/pgaffney/AUXCTMailer

### Excluded from Git (.gitignore)
- `.env` (credentials)
- `venv/` (virtual environment)
- `*.csv` (member data)
- `test_*.html` (test files)
- `sent_emails_*/` (email archives)

### Commit Workflow
```bash
git add auxctmailer/
git commit -m "Description of changes"
git push
```

## Future Maintenance

### When New Training Data Arrives
1. Save new export as `YYYY-MM-DD AUX-CT DB.csv`
2. Update extraction date parameter: `--extraction-date "MM/DD/YYYY"`
3. Test with dry-run first
4. Run production with `--save-html`

### Updating Contact Information
Edit `auxctmailer/templates/training_reminder.html`:
- Line 69: IS officer contact in overdue courses section
- Line 91: General contact line at bottom

### Adding New Courses
1. Add course to `AUX-CT courses.csv`
2. Ensure course code column exists in training CSV
3. No code changes needed (automatically processed)

## SendGrid Free Tier Limits

- **100 emails per day**
- **No email storage** (hence the HTML archiving feature)
- **No scheduling** (run manually or with cron)

If flotilla exceeds 100 members, consider:
1. Upgrading SendGrid plan
2. Running in batches over multiple days
3. Using SMTP instead (configure in `.env`)

## Production Checklist

Before sending:
- [ ] Verify extraction date is correct
- [ ] Test email to yourself looks good
- [ ] Check SendGrid dashboard for available sends
- [ ] Create archive directory: `mkdir sent_emails_YYYY-MM-DD`
- [ ] Dry run shows correct member count
- [ ] `.env` credentials are current

After sending:
- [ ] Verify success count matches expected
- [ ] Check for failed sends in output
- [ ] Archive HTML files: `tar -czf sent_emails_YYYY-MM-DD.tar.gz sent_emails_YYYY-MM-DD/`
- [ ] Verify in SendGrid dashboard

## Contact

Project Owner: Paul Gaffney (FSO-IS)
- Email: paul.gaffney@hey.com
- Phone/Text: 508-904-1393

Original Flotilla: Woods Hole Flotilla 013-11-02 (now supports multiple units)
