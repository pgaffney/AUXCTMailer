"""Tests for main.py CLI entry point."""

import argparse
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from auxctmailer.config import EmailConfig
from auxctmailer.exceptions import ConfigError


class TestBuildArgumentParser:
    """Tests for the argument parser builder."""

    def test_build_argument_parser_returns_argument_parser(self):
        """build_argument_parser() returns a configured ArgumentParser."""
        from auxctmailer.main import build_argument_parser

        parser = build_argument_parser()

        assert isinstance(parser, argparse.ArgumentParser)


class TestSetupAppLogging:
    """Tests for the logging setup helper."""

    def test_setup_app_logging_returns_logger(self):
        """setup_app_logging() returns a logger instance."""
        import logging
        from auxctmailer.main import setup_app_logging

        logger = setup_app_logging(verbose=False, quiet=False)

        assert isinstance(logger, logging.Logger)


class TestHandleDryRun:
    """Tests for the dry-run handler."""

    def test_handle_dry_run_returns_zero(self, tmp_template_dir):
        """handle_dry_run() returns 0 on success."""
        import logging
        from auxctmailer.main import handle_dry_run
        from auxctmailer.mailer import EmailTemplate

        # Minimal args-like object
        class Args:
            template = 'test_template.html'
            subject = 'Test Subject'
            save_html = None
            courses_csv = None
            extraction_date = None

        template = EmailTemplate(tmp_template_dir)
        members = [{'First Name': 'John', 'Last Name': 'Doe', 'Email': 'john@example.com'}]
        logger = logging.getLogger('test')

        result = handle_dry_run(Args(), members, template, logger)

        assert result == 0


class TestMainCLI:
    """Tests for the CLI entry point."""

    def test_dry_run_no_email_sent(self, fixtures_dir, tmp_template_dir, capsys, monkeypatch):
        """--dry-run prevents email sending and shows preview."""
        monkeypatch.setattr(sys, 'argv', [
            'auxctmailer',
            '--training-csv', str(fixtures_dir / 'sample_training.csv'),
            '--email-csv', str(fixtures_dir / 'sample_email.csv'),
            '--template', 'test_template.html',
            '--subject', 'Test Subject',
            '--template-dir', tmp_template_dir,
            '--dry-run',
        ])

        from auxctmailer.main import main
        with patch('auxctmailer.mailer.smtplib.SMTP') as mock_smtp:
            result = main()

        assert result == 0
        mock_smtp.assert_not_called()

    def test_dry_run_with_save_html_generates_files(self, fixtures_dir, tmp_template_dir, tmp_path, monkeypatch):
        """--dry-run --save-html generates HTML files without sending."""
        save_dir = tmp_path / "html_output"
        monkeypatch.setattr(sys, 'argv', [
            'auxctmailer',
            '--training-csv', str(fixtures_dir / 'sample_training.csv'),
            '--email-csv', str(fixtures_dir / 'sample_email.csv'),
            '--template', 'test_template.html',
            '--subject', 'Test Subject',
            '--template-dir', tmp_template_dir,
            '--dry-run',
            '--save-html', str(save_dir),
        ])

        from auxctmailer.main import main
        result = main()

        assert result == 0
        assert save_dir.exists()
        html_files = list(save_dir.glob("*.html"))
        assert len(html_files) == 3  # 3 members in sample data

    def test_missing_sendgrid_key_error(self, fixtures_dir, tmp_template_dir, monkeypatch):
        """Non-dry-run without SendGrid API key returns error."""
        monkeypatch.setattr(sys, 'argv', [
            'auxctmailer',
            '--training-csv', str(fixtures_dir / 'sample_training.csv'),
            '--email-csv', str(fixtures_dir / 'sample_email.csv'),
            '--template', 'test_template.html',
            '--subject', 'Test Subject',
            '--template-dir', tmp_template_dir,
        ])
        # Clear any existing env vars and prevent .env loading
        monkeypatch.delenv('SENDGRID_API_KEY', raising=False)
        monkeypatch.delenv('FROM_EMAIL', raising=False)
        monkeypatch.setenv('EMAIL_PROVIDER', 'sendgrid')

        from auxctmailer.main import main
        with patch('auxctmailer.main.load_dotenv'):  # Prevent loading .env file
            result = main()

        assert result == 1

    def test_invalid_provider_error(self, fixtures_dir, tmp_template_dir, monkeypatch):
        """Unknown email provider returns error."""
        monkeypatch.setattr(sys, 'argv', [
            'auxctmailer',
            '--training-csv', str(fixtures_dir / 'sample_training.csv'),
            '--email-csv', str(fixtures_dir / 'sample_email.csv'),
            '--template', 'test_template.html',
            '--subject', 'Test Subject',
            '--template-dir', tmp_template_dir,
        ])
        monkeypatch.setenv('EMAIL_PROVIDER', 'invalid_provider')

        from auxctmailer.main import main
        result = main()

        assert result == 1

    def test_filter_argument_processing(self, fixtures_dir, tmp_template_dir, tmp_path, monkeypatch):
        """--filter creates correct filtering of members."""
        save_dir = tmp_path / "html_output"
        monkeypatch.setattr(sys, 'argv', [
            'auxctmailer',
            '--training-csv', str(fixtures_dir / 'sample_training.csv'),
            '--email-csv', str(fixtures_dir / 'sample_email.csv'),
            '--template', 'test_template.html',
            '--subject', 'Test Subject',
            '--template-dir', tmp_template_dir,
            '--dry-run',
            '--save-html', str(save_dir),
            '--filter', 'Status=Certified',
        ])

        from auxctmailer.main import main
        result = main()

        assert result == 0
        # Should find 2 Certified members (JOHN DOE and BOB JONES)
        html_files = list(save_dir.glob("*.html"))
        assert len(html_files) == 2

    def test_filter_with_member_number(self, fixtures_dir, tmp_template_dir, tmp_path, monkeypatch):
        """--filter with Member # filters to specific member."""
        save_dir = tmp_path / "html_output"
        monkeypatch.setattr(sys, 'argv', [
            'auxctmailer',
            '--training-csv', str(fixtures_dir / 'sample_training.csv'),
            '--email-csv', str(fixtures_dir / 'sample_email.csv'),
            '--template', 'test_template.html',
            '--subject', 'Test Subject',
            '--template-dir', tmp_template_dir,
            '--dry-run',
            '--save-html', str(save_dir),
            '--filter', 'Member #=1000001',
        ])

        from auxctmailer.main import main
        result = main()

        assert result == 0
        html_files = list(save_dir.glob("*.html"))
        assert len(html_files) == 1

    def test_no_members_returns_zero(self, fixtures_dir, tmp_template_dir, monkeypatch):
        """No matching members exits cleanly with return code 0."""
        monkeypatch.setattr(sys, 'argv', [
            'auxctmailer',
            '--training-csv', str(fixtures_dir / 'sample_training.csv'),
            '--email-csv', str(fixtures_dir / 'sample_email.csv'),
            '--template', 'test_template.html',
            '--subject', 'Test Subject',
            '--template-dir', tmp_template_dir,
            '--dry-run',
            '--filter', 'Status=NonExistent',
        ])

        from auxctmailer.main import main
        result = main()

        assert result == 0

    def test_verbose_flag_accepted(self, fixtures_dir, tmp_template_dir, monkeypatch):
        """--verbose flag is accepted and processed."""
        monkeypatch.setattr(sys, 'argv', [
            'auxctmailer',
            '--training-csv', str(fixtures_dir / 'sample_training.csv'),
            '--email-csv', str(fixtures_dir / 'sample_email.csv'),
            '--template', 'test_template.html',
            '--subject', 'Test Subject',
            '--template-dir', tmp_template_dir,
            '--dry-run',
            '--verbose',
        ])

        from auxctmailer.main import main
        result = main()

        assert result == 0

    def test_quiet_flag_accepted(self, fixtures_dir, tmp_template_dir, monkeypatch):
        """--quiet flag is accepted and processed."""
        monkeypatch.setattr(sys, 'argv', [
            'auxctmailer',
            '--training-csv', str(fixtures_dir / 'sample_training.csv'),
            '--email-csv', str(fixtures_dir / 'sample_email.csv'),
            '--template', 'test_template.html',
            '--subject', 'Test Subject',
            '--template-dir', tmp_template_dir,
            '--dry-run',
            '--quiet',
        ])

        from auxctmailer.main import main
        result = main()

        assert result == 0

    def test_uses_load_email_config_when_not_dry_run(self, fixtures_dir, tmp_template_dir, monkeypatch):
        """main() uses load_email_config() from config module when not in dry-run mode."""
        monkeypatch.setattr(sys, 'argv', [
            'auxctmailer',
            '--training-csv', str(fixtures_dir / 'sample_training.csv'),
            '--email-csv', str(fixtures_dir / 'sample_email.csv'),
            '--template', 'test_template.html',
            '--subject', 'Test Subject',
            '--template-dir', tmp_template_dir,
        ])

        # Setup valid SendGrid config
        monkeypatch.setenv('EMAIL_PROVIDER', 'sendgrid')
        monkeypatch.setenv('SENDGRID_API_KEY', 'SG.test_key')
        monkeypatch.setenv('FROM_EMAIL', 'test@example.com')

        from auxctmailer.main import main

        with patch('auxctmailer.main.load_email_config') as mock_load_config, \
             patch('auxctmailer.main.load_dotenv'), \
             patch('auxctmailer.main.SendGridEmailSender') as mock_sender:
            # Return a valid config
            mock_config = EmailConfig(
                provider='sendgrid',
                from_email='test@example.com',
                sendgrid_api_key='SG.test_key'
            )
            mock_load_config.return_value = mock_config

            # Mock the sender to avoid actual email sending
            mock_sender_instance = MagicMock()
            mock_sender_instance.send_bulk_emails.return_value = {'success': [], 'failed': []}
            mock_sender.return_value = mock_sender_instance

            result = main()

        # Verify load_email_config was called
        mock_load_config.assert_called_once()

    def test_sendgrid_api_client_is_mocked_during_test(self, fixtures_dir, tmp_template_dir, monkeypatch, mock_sendgrid_api):
        """SendGrid API calls go through mock, not real API."""
        monkeypatch.setattr(sys, 'argv', [
            'auxctmailer',
            '--training-csv', str(fixtures_dir / 'sample_training.csv'),
            '--email-csv', str(fixtures_dir / 'sample_email.csv'),
            '--template', 'test_template.html',
            '--subject', 'Test Subject',
            '--template-dir', tmp_template_dir,
        ])

        # Setup SendGrid config via environment
        monkeypatch.setenv('EMAIL_PROVIDER', 'sendgrid')
        monkeypatch.setenv('SENDGRID_API_KEY', 'SG.test_key_for_test')
        monkeypatch.setenv('FROM_EMAIL', 'test@example.com')

        from auxctmailer.main import main
        main()

        # Verify the mock was called (proving real API was not used)
        assert mock_sendgrid_api.send.call_count == 3


class TestCreateEmailSender:
    """Tests for the email sender factory function."""

    def test_create_email_sender_returns_sendgrid_for_sendgrid_provider(self):
        """create_email_sender() returns SendGridEmailSender for sendgrid provider."""
        from auxctmailer.main import create_email_sender
        from auxctmailer.config import EmailConfig
        from auxctmailer.mailer import SendGridEmailSender

        config = EmailConfig(
            provider='sendgrid',
            from_email='test@example.com',
            sendgrid_api_key='SG.test_key'
        )

        sender = create_email_sender(config)

        assert isinstance(sender, SendGridEmailSender)

    def test_create_email_sender_returns_smtp_for_smtp_provider(self):
        """create_email_sender() returns EmailSender for smtp provider."""
        from auxctmailer.main import create_email_sender
        from auxctmailer.config import EmailConfig
        from auxctmailer.mailer import EmailSender

        config = EmailConfig(
            provider='smtp',
            from_email='test@example.com',
            smtp_host='smtp.example.com',
            smtp_port=587,
            smtp_user='user',
            smtp_password='pass',
            smtp_use_tls=True
        )

        sender = create_email_sender(config)

        assert isinstance(sender, EmailSender)


class TestParseFilterCriteria:
    """Tests for the filter criteria parser."""

    def test_parse_filter_criteria_returns_empty_dict_for_none(self):
        """parse_filter_criteria() returns empty dict when input is None."""
        from auxctmailer.main import parse_filter_criteria

        result = parse_filter_criteria(None)

        assert result == {}

    def test_parse_filter_criteria_parses_key_value_pairs(self):
        """parse_filter_criteria() parses 'KEY=VALUE' format."""
        from auxctmailer.main import parse_filter_criteria

        result = parse_filter_criteria(['Status=Certified'])

        assert result == {'Status': 'Certified'}
