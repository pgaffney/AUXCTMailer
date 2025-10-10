"""Tests for exceptions module."""

import pytest
from auxctmailer.exceptions import (
    AUXCTMailerError,
    MemberDataError,
    EmailSendError,
    TemplateError,
    ConfigError,
)


class TestExceptions:
    """Tests for custom exception classes."""

    def test_base_exception(self):
        """Test base AUXCTMailerError can be raised and caught."""
        with pytest.raises(AUXCTMailerError):
            raise AUXCTMailerError("Test error")

    def test_member_data_error(self):
        """Test MemberDataError inherits from base exception."""
        with pytest.raises(AUXCTMailerError):
            raise MemberDataError("Failed to load member data")

    def test_email_send_error(self):
        """Test EmailSendError inherits from base exception."""
        with pytest.raises(AUXCTMailerError):
            raise EmailSendError("Failed to send email")

    def test_template_error(self):
        """Test TemplateError inherits from base exception."""
        with pytest.raises(AUXCTMailerError):
            raise TemplateError("Template rendering failed")

    def test_config_error(self):
        """Test ConfigError inherits from base exception."""
        with pytest.raises(AUXCTMailerError):
            raise ConfigError("Invalid configuration")

    def test_exception_message(self):
        """Test exception messages are preserved."""
        error_message = "Specific error details"
        try:
            raise MemberDataError(error_message)
        except MemberDataError as e:
            assert str(e) == error_message

    def test_catch_specific_exception(self):
        """Test catching specific exception types."""
        with pytest.raises(MemberDataError):
            raise MemberDataError("Data error")

        # Should not catch EmailSendError
        with pytest.raises(EmailSendError):
            raise EmailSendError("Send error")
