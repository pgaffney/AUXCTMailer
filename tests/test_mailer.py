"""Tests for mailer module."""

import pytest


class TestMailerFixtures:
    """Tests to verify mailer test fixtures work correctly."""

    def test_mock_smtp_fixture_exists(self, mock_smtp):
        """Verify mock_smtp fixture provides a mock SMTP connection."""
        # The fixture should provide a mock that can be used to verify email sending
        assert mock_smtp is not None

    def test_mock_sendgrid_client_fixture_exists(self, mock_sendgrid_client):
        """Verify mock_sendgrid_client fixture provides a mock SendGrid client."""
        assert mock_sendgrid_client is not None

    def test_sample_member_data_fixture_has_required_fields(self, sample_member_data):
        """Verify sample_member_data fixture provides dict with typical member fields."""
        assert isinstance(sample_member_data, dict)
        assert 'first_name' in sample_member_data
        assert 'last_name' in sample_member_data
        assert 'email' in sample_member_data
        assert 'member_num' in sample_member_data

    def test_tmp_template_dir_fixture_contains_test_template(self, tmp_template_dir):
        """Verify tmp_template_dir fixture provides directory with test_template.html."""
        from pathlib import Path
        template_path = Path(tmp_template_dir) / "test_template.html"
        assert template_path.exists()
