# AUXCTMailer Project Documentation

## Project Overview

AUXCTMailer is an email automation system for the U.S. Coast Guard Auxiliary. It sends personalized training and task status emails to members.

**Primary Use Cases:**
1. **Task Status Reports** (NEW): Comprehensive status reports from xlsx "To Do Lists" exports showing all member tasks across all competency types with red/yellow/green priority coding.
2. **AUXCT Training Reminders** (Legacy): Training reminders from CSV exports focused on core training courses.

## Key Features

- ✅ **Task Status Reports** - Comprehensive task tracking across all competency types (AUXCT, Boat Crew, Instructor, Vessel Examiner, etc.)
- ✅ **Priority-coded sections** - Red (urgent/overdue), Yellow (due within 365 days), Green (good standing)
- ✅ **xlsx support** - Load data from "To Do Lists for all members" xlsx exports
- ✅ **Multi-unit support** - Dynamic unit name and number lookup from UnitDetails.csv
- ✅ **Pretty formatting** - Unit names (Title Case + "Flotilla" suffix) and numbers (DDD-VV-UU format)
- ✅ Personalized emails with member-specific task requirements
- ✅ Currency tracking for hours/exams/visits (shows progress like "0/5 required")
- ✅ SendGrid and SMTP email provider support
- ✅ HTML archiving of sent emails (important for SendGrid free tier)
- ✅ Dry-run mode for testing

## Project Structure

```
AUXCTMailer/
├── auxctmailer/
│   ├── __init__.py
│   ├── main.py              # CLI entry point (legacy CSV workflow)
│   ├── status_report.py     # CLI entry point (NEW xlsx workflow)
│   ├── xlsx_loader.py       # xlsx data loading and task categorization
│   ├── database.py          # CSV data loading and member filtering (legacy)
│   ├── mailer.py            # Email sending and template rendering
│   ├── context.py           # Template context processing
│   └── templates/
│       ├── task_status_report.html  # NEW: Priority-coded status report template
│       ├── training_reminder.html   # Legacy: AUXCT training reminder template
│       └── example.html             # Sample template
├── .env                     # SendGrid credentials (NOT in Git)
├── .env.example            # Environment variable template
├── .gitignore
├── requirements.txt
├── setup.py
├── README.md
└── CLAUDE.md               # This file

# Data Files (NOT in Git):
├── *To Do Lists for all members*.xlsx  # NEW: xlsx export from member management
├── MemberEmail.csv                      # Member emails
├── UnitDetails.csv                      # Unit names and details (optional)
├── 2025-10-01 AUX-CT DB.csv            # Legacy: CSV training data export
└── AUX-CT courses.csv                   # Legacy: Course information
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

1. **To Do Lists xlsx** (NEW - Primary): `*To Do Lists for all members*.xlsx`
   - Export from member management system showing all member tasks
   - Contains: Unit/Member Name/ID, Competency Type, Competency Status, Task Type, Task Next Due, Task Last Completed, Cycle Requirement, Currency Units
   - Multiple rows per member (one per task)
   - Supports 17+ competency types: AUXCT, Boat Crew, Instructor, Vessel Examiner, etc.
   - Supports 33+ task types: training courses, currency hours, exams, qualification tasks

2. **Email CSV:** `MemberEmail.csv`
   - Contains: Member ID, Last Name, First Name, Email
   - Required for matching emails to member IDs from xlsx

3. **Units CSV:** `UnitDetails.csv` (optional)
   - Contains: Unit Number, Unit Name, Type, Last Modified Date, FSO-IS, FSO-MT
   - Used for dynamic unit name lookup
   - Unit Number format: 7 digits (DDDVVUU - District/Division/Unit)
   - Unit names are auto-prettified: "WOODS HOLE FLOTILLA" → "Woods Hole Flotilla"

4. **Legacy CSV Files** (for training_reminder.html workflow):
   - `AUX-CT DB.csv` - Training data with course columns
   - `AUX-CT courses.csv` - Course metadata with enrollment keys

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

---

## Task Status Report Commands (NEW - xlsx workflow)

### Test Status Report (Single member, dry-run)

```bash
python -m auxctmailer.status_report \
  --xlsx "013-11-02 To Do Lists for all members-2026-01-20-14-04-19.xlsx" \
  --email-csv MemberEmail.csv \
  --filter-member 5008388 \
  --dry-run \
  --save-html test_status_reports
```

### Dry Run (Preview all members)

```bash
python -m auxctmailer.status_report \
  --xlsx "013-11-02 To Do Lists for all members-2026-01-20-14-04-19.xlsx" \
  --email-csv MemberEmail.csv \
  --dry-run \
  --save-html test_status_reports
```

### Production Run (Send to all members)

```bash
python -m auxctmailer.status_report \
  --xlsx "013-11-02 To Do Lists for all members-2026-01-20-14-04-19.xlsx" \
  --email-csv MemberEmail.csv \
  --units-csv UnitDetails.csv \
  --save-html sent_status_reports_YYYY-MM-DD
```

### Filter Options (Status Report)

Only members with urgent (red) tasks:
```bash
--filter-has-red
```

Only members with attention-needed (yellow/red) tasks:
```bash
--filter-has-yellow
```

Single member by ID:
```bash
--filter-member 5008388
```

**Important:** Always use `--save-html` to archive sent emails!

---

## Legacy Training Reminder Commands (CSV workflow)

### Test Email (Single member)

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
  --extraction-date "10/01/2025" \
  --template training_reminder.html \
  --subject "AUXCT Training Reminder - {{ first_name }} {{ last_name }}" \
  --dry-run
```

### Filter Options (Legacy)

Filter by specific member:
```bash
--filter "Member #=1244671"
```

Filter by status:
```bash
--filter Status=Certified
```

## Email Template Personalization

### Task Status Report Template (task_status_report.html)

Template variables for the new xlsx-based status reports:

**Member Information:**
- `{{ first_name }}` / `{{ first_name_titlecase }}` - Name (PAUL → Paul)
- `{{ last_name }}`
- `{{ member_num }}` / `{{ member_id }}`
- `{{ unit_number }}` / `{{ unit_number_pretty }}` (e.g., "013-11-02")
- `{{ unit_name_pretty }}` (e.g., "Woods Hole Flotilla")
- `{{ report_date }}` - Date report was generated

**Task Lists (by priority):**
- `{{ tasks_red }}` - List of urgent/overdue tasks
- `{{ tasks_yellow }}` - List of attention-needed tasks
- `{{ tasks_green }}` - List of tasks in good standing
- `{{ has_red_tasks }}` / `{{ has_yellow_tasks }}` / `{{ has_green_tasks }}` - Booleans

**Each task in lists contains:**
- `task_type` - Task name (e.g., "VESSEL EXAMINATIONS")
- `competency_type` - Competency area (e.g., "VESSEL EXAMINER")
- `competency_status` - Status (e.g., "Certified", "REYR")
- `task_next_due` - Due date string (e.g., "12/31/2026")
- `days_until_due` - Days until due (None if overdue)
- `days_overdue` - Days overdue (None if not overdue)
- `cycle_requirement` - Required count (e.g., 5.0 for exams)
- `currency_units` - Current progress (e.g., 0.0)

---

### Legacy Training Reminder Template (training_reminder.html)

Template variables for the CSV-based training reminders:

**Member Information:**
- `{{ first_name }}` - Auto-converted to title case (PAUL → Paul)
- `{{ last_name }}`
- `{{ member_num }}`
- `{{ status }}` - Certified, REYR, etc.
- `{{ uniform_inspection }}` - Date of last inspection
- `{{ uniform_exempt }}` - Boolean, true if exempt
- `{{ extraction_date }}` - Date training data was extracted
- `{{ unit_number_pretty }}` - Formatted unit number (e.g., "013-11-02")
- `{{ unit_name_pretty }}` - Formatted unit name (e.g., "Woods Hole Flotilla")

**Course Warnings:**
- `{% if has_overdue_courses %}` - Red warning section
- `{% if has_due_soon_courses %}` - Yellow warning section
- `{{ courses_overdue }}` - List with: title, url, enrollment_code, days_overdue
- `{{ courses_due_soon }}` - List with: title, url, enrollment_code, days_until_due, due_date

## Data Processing Logic

### Task Urgency (Status Report)

Tasks are categorized by urgency based on their due date:

- **Red (Urgent)**: Task is overdue OR due within 30 days
- **Yellow (Attention)**: Task is due within 365 days (but more than 30 days out)
- **Green (Good)**: Task is due more than 365 days out OR has no due date

Special cases:
- Tasks with no due date but requiring completion (cycle_requirement > 0) are marked yellow
- Tasks with no due date and no cycle requirement are marked green

### Uniform Inspection (Legacy)
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
