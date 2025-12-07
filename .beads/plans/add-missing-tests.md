# Implementation Plan: Add Missing Tests for Email Sending

## Problem Statement

The AUXCTMailer has solid test coverage for data processing (`database.py`, `context.py`, `config.py`, `exceptions.py`, `logger.py`) but **zero test coverage** for the core email sending functionality in `mailer.py` and CLI orchestration in `main.py`. This creates risk when refactoring and leaves critical paths untested.

## Scope

**In scope:**
- Unit tests for `EmailTemplate` class (template rendering)
- Unit tests for `EmailSender` class (SMTP sending with mocked SMTP)
- Unit tests for `SendGridEmailSender` class (SendGrid API with mocked client)
- Unit tests for `send_bulk_emails` method (orchestration)
- Integration tests for `main.py` CLI (argument parsing, dry-run mode, HTML generation)

**Out of scope:**
- Actual email sending (all external calls will be mocked)
- Performance testing
- End-to-end tests with real SendGrid/SMTP

## Acceptance Criteria

### 1. EmailTemplate Tests
- Given a template directory and template file, when `render()` is called with context, then the template variables are substituted correctly
- Given a template string, when `render_string()` is called with context, then the string is rendered correctly
- Given an invalid template name, when `render()` is called, then a TemplateError is raised
- Given a template with missing required variables, when `render()` is called, then appropriate behavior occurs

### 2. EmailSender (SMTP) Tests
- Given valid SMTP credentials, when `send_email()` is called, then SMTP connection is established and email is sent
- Given TLS enabled, when `send_email()` is called, then `starttls()` is invoked
- Given SMTP connection failure, when `send_email()` is called, then False is returned and error is logged
- Given SMTP authentication failure, when `send_email()` is called, then False is returned
- Given no `from_email` provided, when `send_email()` is called, then username is used as sender

### 3. SendGridEmailSender Tests
- Given valid API key, when `send_email()` is called, then SendGrid client sends the message
- Given SendGrid returns 202, when `send_email()` is called, then True is returned
- Given SendGrid returns error status, when `send_email()` is called, then False is returned
- Given SendGrid raises exception, when `send_email()` is called, then False is returned and error is logged
- Given plain text content provided, when `send_email()` is called, then both HTML and text content are included

### 4. send_bulk_emails Tests
- Given list of recipients, when `send_bulk_emails()` is called, then each recipient receives personalized email
- Given recipient without email, when `send_bulk_emails()` is called, then that recipient is skipped
- Given `save_html_dir` provided, when emails are sent successfully, then HTML files are saved
- Given mixed success/failure, when `send_bulk_emails()` completes, then results dict has correct counts
- Given template context, when `send_bulk_emails()` is called, then context is normalized before rendering

### 5. Main CLI Tests
- Given required arguments, when `main()` is called, then argument parser processes them correctly
- Given `--dry-run` flag, when `main()` is called, then no emails are sent and preview is shown
- Given `--dry-run --save-html`, when `main()` is called, then HTML files are generated without sending
- Given invalid email provider in env, when `main()` is called, then error is returned
- Given missing SendGrid API key (non-dry-run), when `main()` is called, then error is returned
- Given `--filter` argument, when `main()` is called, then only matching members are processed
- Given `--verbose` flag, when `main()` is called, then DEBUG logging is enabled
- Given `--quiet` flag, when `main()` is called, then WARNING logging is enabled

## Technical Approach

### Test File Structure
```
tests/
├── test_mailer.py          # New: EmailTemplate, EmailSender, SendGridEmailSender tests
├── test_main.py            # New: CLI integration tests
├── conftest.py             # Shared fixtures (mock SMTP, mock SendGrid, sample data)
└── fixtures/
    └── templates/
        └── test_template.html  # Test email template
```

### Mocking Strategy

**SMTP:** Use `unittest.mock.patch` on `smtplib.SMTP` to avoid real connections:
```python
@patch('auxctmailer.mailer.smtplib.SMTP')
def test_send_email_success(self, mock_smtp):
    mock_server = MagicMock()
    mock_smtp.return_value = mock_server
    # ... test code
```

**SendGrid:** Patch `SendGridAPIClient.send`:
```python
@patch.object(SendGridAPIClient, 'send')
def test_sendgrid_success(self, mock_send):
    mock_send.return_value = MagicMock(status_code=202)
    # ... test code
```

**Environment Variables:** Use `pytest-env` or `monkeypatch`:
```python
def test_sendgrid_config(monkeypatch):
    monkeypatch.setenv('EMAIL_PROVIDER', 'sendgrid')
    monkeypatch.setenv('SENDGRID_API_KEY', 'test-key')
    # ... test code
```

**File System:** Use `tmp_path` fixture for HTML file generation tests.

### Test Organization

Each test class follows the pattern:
1. Setup fixtures for common test data
2. Test happy path first
3. Test error conditions
4. Test edge cases

## Implementation Tasks

1. **Create test fixtures and conftest.py**
   - Sample member data
   - Mock SMTP server
   - Mock SendGrid client
   - Test template file

2. **Add EmailTemplate tests**
   - `render()` success
   - `render_string()` success
   - Missing template error
   - Template syntax error

3. **Add EmailSender (SMTP) tests**
   - Successful send
   - TLS connection
   - Connection failure
   - Auth failure
   - Default from_email

4. **Add SendGridEmailSender tests**
   - Successful send (202 response)
   - API error response
   - Exception handling
   - With/without plain text

5. **Add send_bulk_emails tests**
   - Multiple recipients
   - Missing email handling
   - HTML file saving
   - Results tracking

6. **Add main.py CLI tests**
   - Argument parsing
   - Dry-run mode
   - HTML generation in dry-run
   - Environment validation
   - Filter processing
   - Logging levels

## Dependencies

- `pytest` (already in project)
- `pytest-mock` (may need to add)
- No additional external dependencies needed

## Risks

1. **SendGrid SDK internal changes** - Mitigate by mocking at the right level
2. **SMTP behavior variations** - Test with standard mock patterns
3. **Template rendering complexity** - Keep test templates simple
