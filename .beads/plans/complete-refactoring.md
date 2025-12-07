# Plan: Complete main.py Refactoring

## Current State

The main.py refactoring effort is nearly complete. The following tasks have been completed:
- ✅ Extract `build_argument_parser()` function
- ✅ Extract `setup_app_logging()` helper function
- ✅ Extract `handle_dry_run()` function
- ✅ Replace duplicated config validation with `load_email_config()`
- ✅ Add comprehensive unit tests for all extracted functions
- ✅ Add CLI integration tests

## Remaining Tasks

Two refactoring tasks remain open:

### 1. Extract `create_email_sender()` Function (AUXCTMailer-bgf, P2)

**Current Code (lines 218-230):**
```python
if email_config.provider == 'sendgrid':
    sender = SendGridEmailSender(
        api_key=email_config.sendgrid_api_key,
        from_email=email_config.from_email
    )
else:  # smtp
    sender = EmailSender(
        smtp_host=email_config.smtp_host,
        smtp_port=email_config.smtp_port,
        username=email_config.smtp_user,
        password=email_config.smtp_password,
        use_tls=email_config.smtp_use_tls
    )
```

**Target:**
```python
def create_email_sender(config: EmailConfig):
    """Create the appropriate email sender based on config."""
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
```

**Tests to Add:**
1. `test_create_email_sender_returns_sendgrid_for_sendgrid_provider`
2. `test_create_email_sender_returns_smtp_for_smtp_provider`

### 2. Extract `parse_filter_criteria()` Function (AUXCTMailer-ik5, P3)

**Current Code (lines 192-197):**
```python
if args.filter:
    criteria = {}
    for f in args.filter:
        if '=' in f:
            key, value = f.split('=', 1)
            criteria[key] = value
```

**Target:**
```python
def parse_filter_criteria(filter_args: list[str] | None) -> dict:
    """Parse filter arguments into a criteria dictionary.

    Args:
        filter_args: List of 'KEY=VALUE' strings, or None

    Returns:
        Dictionary of filter criteria
    """
    if not filter_args:
        return {}
    criteria = {}
    for f in filter_args:
        if '=' in f:
            key, value = f.split('=', 1)
            criteria[key] = value
    return criteria
```

**Tests to Add:**
1. `test_parse_filter_criteria_returns_empty_dict_for_none`
2. `test_parse_filter_criteria_parses_key_value_pairs`
3. `test_parse_filter_criteria_handles_multiple_filters`
4. `test_parse_filter_criteria_ignores_malformed_input`
5. `test_parse_filter_criteria_handles_value_with_equals_sign`

## Implementation Order

1. **Task 1: create_email_sender()** - Higher priority (P2), has a dependency that is already closed
2. **Task 2: parse_filter_criteria()** - Lower priority (P3), no dependencies

## Acceptance Criteria

For each task:
- [ ] Write failing tests first
- [ ] Extract the function
- [ ] Update main() to use the new function
- [ ] All tests pass
- [ ] Close the beads issue

## Notes

- Both extractions are simple refactors with no functional changes
- Existing integration tests verify end-to-end behavior is preserved
- Type hints should be added to match the existing code style
