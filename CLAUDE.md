# AUXCTMailer Project Documentation

## Project Overview

AUXCTMailer is an email automation system for the U.S. Coast Guard Auxiliary. It sends personalized training and task status emails to members.

**Primary Use Cases:**
1. **Task Status Reports** (NEW): Comprehensive status reports from xlsx "To Do Lists" exports showing all member tasks across all competency types with red/yellow/green priority coding.
2. **AUXCT Training Reminders** (Legacy): Training reminders from CSV exports focused on core training courses.

## Key Features

- ✅ **Task Status Reports** - Comprehensive task tracking across all competency types (AUXCT, Boat Crew, Instructor, Vessel Examiner, etc.)
- ✅ **"All Good" Reports** - Members without task maintenance requirements receive a status confirmation email
- ✅ **Priority-coded sections** - Red (Expired), Yellow (Not Yet Completed), Blue (In Progress), Green (Completed)
- ✅ **xlsx support** - Load data from multiple xlsx exports (To Do List, Unit Members, Competencies, Officers)
- ✅ **Smart email sourcing** - Uses emails from Unit Members xlsx as primary source (more current than CSV)
- ✅ **Multi-unit support** - Dynamic unit name and number lookup from UnitDetails.csv
- ✅ **Pretty formatting** - Unit names (Title Case + "Flotilla" suffix) and numbers (DDD-VV-UU format)
- ✅ Personalized emails with member-specific task requirements
- ✅ Currency tracking for hours/exams/visits (shows progress like "0/5 required")
- ✅ SendGrid and SMTP email provider support (SMTP fallback for Outlook/Comcast addresses)
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
│       ├── task_status_report.html  # Status report for members with tasks
│       ├── no_tasks_report.html     # "All good" report for members without tasks
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
├── *To Do List by Member*.xlsx          # Task data with Task Status field
├── *Unit Members - EM, PH*.xlsx         # Member info with emails/phones (primary email source)
├── *Unit Summary - Competencies*.xlsx   # Competency status dates
├── *Officers - Current*.xlsx            # FSO contact info
├── MemberEmail.csv                      # Member emails (fallback)
├── UnitDetails.csv                      # Unit names and details
├── AUX-CT courses.csv                   # Course URLs and enrollment codes
├── 2025-10-01 AUX-CT DB.csv            # Legacy: CSV training data export
└── competency_fso_mapping.json          # Maps competencies to FSO positions
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

1. **To Do List by Member xlsx** (Required): `*To Do List by Member*.xlsx`
   - Export from AUXDATA showing all member tasks
   - Must include **Task Status** column (Expired, Not Yet Completed, In Progress, Completed)
   - Contains: Unit/Member Name/ID, Competency Type, Competency Status, Task Type, Task Status, Task Next Due, Task Last Completed, Cycle Requirement, Currency Units
   - Multiple rows per member (one per task)

2. **Unit Members xlsx** (Required): `*Unit Members - EM, PH*.xlsx`
   - Export from AUXDATA with member contact info
   - **Primary source for email addresses** (more current than CSV)
   - Contains: Member ID, Name, Status, Email, Phone, Uniform Inspection date
   - Members in this file but NOT in task data receive "all good" emails

3. **Unit Summary - Competencies xlsx** (Optional): `*Unit Summary - Competencies*.xlsx`
   - Complete list of member competencies with status dates
   - Used to populate the "Your Qualifications" table in emails

4. **Officers xlsx** (Optional): `*Officers - Current*.xlsx`
   - Current unit officers with contact info
   - Used for FSO-IS and FSO-MT contact info in emails

5. **Email CSV:** `MemberEmail.csv` (Fallback)
   - Contains: Member ID, Last Name, First Name, Email
   - Used as fallback if member not in Unit Members xlsx

6. **Units CSV:** `UnitDetails.csv` (Optional)
   - Contains: Unit Number, Unit Name, Type
   - Used for dynamic unit name lookup
   - Unit Number format: 7 digits (DDDVVUU - District/Division/Unit)
   - Unit names are auto-prettified: "WOODS HOLE FLOTILLA" → "Woods Hole Flotilla"

7. **Courses CSV:** `AUX-CT courses.csv` (Optional)
   - Course URLs and enrollment codes for AUXCT tasks
   - Adds "Take this course" links to training tasks

8. **Legacy CSV Files** (for training_reminder.html workflow):
   - `AUX-CT DB.csv` - Training data with course columns

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

## Task Status Report Commands (xlsx workflow)

### Test Status Report (Single member, dry-run)

```bash
python -m auxctmailer.status_report \
  --xlsx "013-11-02 To Do List by Member-2026-01-28-09-40-20.xlsx" \
  --competencies-xlsx "013-11-02 Unit Summary - Competencies-2026-01-28-09-35-17.xlsx" \
  --members-xlsx "013-11-02 Unit Members - EM, PH-2026-01-28-09-32-19.xlsx" \
  --email-csv MemberEmail.csv \
  --units-csv UnitDetails.csv \
  --filter-member 5008388 \
  --dry-run \
  --save-html test_status_reports
```

### Dry Run (Preview all members)

```bash
python -m auxctmailer.status_report \
  --xlsx "013-11-02 To Do List by Member-2026-01-28-09-40-20.xlsx" \
  --competencies-xlsx "013-11-02 Unit Summary - Competencies-2026-01-28-09-35-17.xlsx" \
  --members-xlsx "013-11-02 Unit Members - EM, PH-2026-01-28-09-32-19.xlsx" \
  --email-csv MemberEmail.csv \
  --units-csv UnitDetails.csv \
  --courses-csv "AUX-CT courses.csv" \
  --officers-xlsx "013 - Officers - Current-2026-01-21-06-57-22.xlsx" \
  --dry-run \
  --save-html test_status_reports
```

### Production Run (Send to all members)

```bash
python -m auxctmailer.status_report \
  --xlsx "013-11-02 To Do List by Member-2026-01-28-09-40-20.xlsx" \
  --competencies-xlsx "013-11-02 Unit Summary - Competencies-2026-01-28-09-35-17.xlsx" \
  --members-xlsx "013-11-02 Unit Members - EM, PH-2026-01-28-09-32-19.xlsx" \
  --email-csv MemberEmail.csv \
  --units-csv UnitDetails.csv \
  --courses-csv "AUX-CT courses.csv" \
  --officers-xlsx "013 - Officers - Current-2026-01-21-06-57-22.xlsx" \
  --save-html sent_status_reports_2026-01-28
```

### Filter Options (Status Report)

Only members with urgent (red/expired) tasks:
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

Exclude members without tasks (only send to members with task data):
```bash
--exclude-no-tasks
```

**Important:** Always use `--save-html` to archive sent emails!

### Email Distribution

By default, **all members** receive emails:
- Members **with tasks** → `task_status_report.html` (priority-coded task list)
- Members **without tasks** (BQ/AP status) → `no_tasks_report.html` ("all good" confirmation)

Use `--exclude-no-tasks` to skip the "all good" emails if desired.

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

Tasks are categorized by the **Task Status** field from the xlsx export:

| Task Status | Color | Meaning |
|-------------|-------|---------|
| Expired | Red | Task is overdue, immediate action required |
| Not Yet Completed | Yellow | Task needs attention |
| In Progress | Blue | Task is being worked on |
| Completed | Green | Task is done for this cycle |

**Important:** The xlsx export must include the "Task Status" column. Configure your AUXDATA report to show this field.

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

Format: `{LAST_NAME}_{FIRST_NAME}_{member_num}.html`

Examples:
- `GAFFNEY_PAUL_5008388.html`
- `FARREN_MARILYN_1143581.html`

**Why:** SendGrid free tier doesn't store sent emails, so these provide a local record of exactly what was sent to each member.

## Troubleshooting

### SendGrid Delivery Issues (Outlook, Comcast, Juno)

Some email providers have issues with SendGrid. Use SMTP fallback:

1. Edit `.env` to switch provider:
   ```bash
   EMAIL_PROVIDER=smtp
   ```

2. Resend to specific member:
   ```bash
   python -m auxctmailer.status_report \
     --xlsx "..." --members-xlsx "..." --email-csv MemberEmail.csv \
     --filter-member 1234567 \
     --save-html sent_status_reports_2026-01-28
   ```

3. Switch back to SendGrid:
   ```bash
   EMAIL_PROVIDER=sendgrid
   ```

### SendGrid 401 Unauthorized
- Check API key in `.env` file
- Verify API key format starts with `SG.`
- Ensure API key has "Mail Send" permissions

### Missing Members
- Members must be in Unit Members xlsx OR MemberEmail.csv to receive email
- Members in task data but not in Unit Members xlsx will use MemberEmail.csv
- Check Member # matches between files

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

### When New Data Arrives
1. Export from AUXDATA:
   - "To Do List by Member" (must include Task Status column)
   - "Unit Members - EM, PH" (for email addresses)
   - "Unit Summary - Competencies" (optional, for qualification dates)
   - "Officers - Current" (optional, for FSO contacts)
2. Place xlsx files in project directory
3. Update filenames in command
4. Test with `--dry-run --save-html test_output`
5. Run production with `--save-html sent_status_reports_YYYY-MM-DD`

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
- [ ] Export fresh data from AUXDATA (To Do List must have Task Status column)
- [ ] Place all xlsx files in project directory
- [ ] Test with `--filter-member YOUR_ID --dry-run` to preview your own email
- [ ] Check SendGrid dashboard for available sends (100/day free tier)
- [ ] Dry run shows correct member count (should match unit roster)
- [ ] `.env` credentials are current

After sending:
- [ ] Verify success count matches expected
- [ ] Check SendGrid for "not_delivered" or "processing" status
- [ ] Resend failed emails via SMTP if needed (Outlook/Comcast issues)
- [ ] Archive HTML files: `tar -czf sent_status_reports_YYYY-MM-DD.tar.gz sent_status_reports_YYYY-MM-DD/`

## Contact

Project Owner: Paul Gaffney (FSO-IS)
- Email: paul.gaffney@hey.com
- Phone/Text: 508-904-1393

Original Flotilla: Woods Hole Flotilla 013-11-02 (now supports multiple units)
