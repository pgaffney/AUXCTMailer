"""Tests for main.py CLI entry point."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock


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
