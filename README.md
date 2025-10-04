# AUXCTMailer

Email automation system for sending custom emails to AUXCT members based on database records.

## Features

- Load member records from CSV files
- Filter members by any column criteria
- Send personalized emails using Jinja2 templates
- Bulk email sending with success/failure tracking
- Dry-run mode to preview emails before sending
- Environment-based SMTP configuration

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

Send emails to all certified members:

```bash
auxctmailer \
  --training-csv "2025-10-01 AUX-CT DB.csv" \
  --email-csv MemberEmail.csv \
  --template training_reminder.html \
  --subject "AUXCT Training Status Update"
```

### Filter Members

Send emails only to members matching specific criteria:

```bash
auxctmailer \
  --training-csv "2025-10-01 AUX-CT DB.csv" \
  --email-csv MemberEmail.csv \
  --template training_reminder.html \
  --subject "Training Reminder" \
  --filter Status=Certified
```

### Dry Run

Preview what would be sent without actually sending emails:

```bash
auxctmailer \
  --training-csv "2025-10-01 AUX-CT DB.csv" \
  --email-csv MemberEmail.csv \
  --template training_reminder.html \
  --subject "Important Reminder" \
  --filter Status=Certified \
  --dry-run
```

### Command Line Options

- `--training-csv PATH` - Path to CSV file with training/competency records (required)
- `--email-csv PATH` - Path to CSV file with member emails (required)
- `--template NAME` - Email template filename in `auxctmailer/templates/` (required)
- `--subject TEXT` - Email subject line, can use Jinja2 variables (required)
- `--filter KEY=VALUE` - Filter members by column values (optional, multiple allowed)
- `--dry-run` - Preview emails without sending (optional)
- `--template-dir PATH` - Custom templates directory (optional)

## CSV Format

The system uses two CSV files that are joined on Member ID/Member #:

### Training CSV
Contains member training and competency data with columns like:
- `Member #` - Member identifier (used for joining)
- `Status` - Certification status (e.g., "Certified")
- `Uniform Inspection` - Date
- `Any Due?` - Y/N indicator
- Various competency columns (CRA, PAWR, POSH, etc.)

### Email CSV
Contains member contact information:
- `Member ID` - Member identifier (used for joining)
- `First Name`
- `Last Name`
- `Email` - Email address

The two files are automatically joined on `Member #` / `Member ID`.

## Email Templates

Create HTML email templates in `auxctmailer/templates/` using Jinja2 syntax:

**training_reminder.html** (example included):
```html
<html>
<body>
  <h1>Hello {{ first_name }}!</h1>
  <p>Member #: {{ member_num }}</p>
  <p>Status: {{ status }}</p>

  {% if status == 'Certified' %}
  <p>Your training is up to date!</p>
  {% else %}
  <p>Please complete your training requirements.</p>
  {% endif %}
</body>
</html>
```

**Template Variables**: All CSV columns are available as template variables. Column names with spaces or special characters are automatically normalized (e.g., `First Name` becomes `first_name`, `Member #` becomes `member_num`, `Any Due?` becomes `any_due`).

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

## Security Notes

- Never commit `.env` files or CSV files with real member data
- Use app-specific passwords for Gmail (not your main password)
- CSV files are excluded from git via `.gitignore`
- Consider encrypting sensitive member data at rest

## Example Workflow

1. Export member data to CSV
2. Create email template in `auxctmailer/templates/`
3. Test with dry-run: `auxctmailer --csv members.csv --template new_template.html --subject "Test" --dry-run`
4. Send to filtered subset first: `auxctmailer --csv members.csv --template new_template.html --subject "Test" --filter status=test`
5. Send to all: `auxctmailer --csv members.csv --template new_template.html --subject "Live Send"`
