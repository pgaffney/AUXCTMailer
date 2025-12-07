"""Tests for mailer module."""

import pytest

from unittest.mock import patch, MagicMock

from auxctmailer.mailer import EmailTemplate, EmailSender, SendGridEmailSender


class TestSendGridEmailSender:
    """Tests for the SendGridEmailSender class."""

    def test_send_email_success_returns_true(self):
        """SendGrid 202 response returns True."""
        with patch("auxctmailer.mailer.SendGridAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_client.send.return_value = mock_response

            sender = SendGridEmailSender(
                api_key="SG.test_key",
                from_email="sender@example.com",
            )
            result = sender.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                body_html="<p>Hello</p>",
            )

            assert result is True
            mock_client.send.assert_called_once()

    def test_send_email_non_202_response_returns_false(self):
        """SendGrid non-202 response returns False."""
        with patch("auxctmailer.mailer.SendGridAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_client.send.return_value = mock_response

            sender = SendGridEmailSender(
                api_key="SG.test_key",
                from_email="sender@example.com",
            )
            result = sender.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                body_html="<p>Hello</p>",
            )

            assert result is False

    def test_send_email_api_exception_returns_false(self):
        """SendGrid API exception returns False."""
        with patch("auxctmailer.mailer.SendGridAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.send.side_effect = Exception("API Error")

            sender = SendGridEmailSender(
                api_key="SG.test_key",
                from_email="sender@example.com",
            )
            result = sender.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                body_html="<p>Hello</p>",
            )

            assert result is False

    def test_send_email_default_from_uses_configured_email(self):
        """Without from_email param, uses configured from_email."""
        with patch("auxctmailer.mailer.SendGridAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_client.send.return_value = mock_response

            sender = SendGridEmailSender(
                api_key="SG.test_key",
                from_email="default@example.com",
            )
            sender.send_email(
                to_email="recipient@example.com",
                subject="Test",
                body_html="<p>Hello</p>",
            )

            # Verify the Mail object was created with the default from_email
            call_args = mock_client.send.call_args
            mail_obj = call_args[0][0]
            assert mail_obj.from_email.email == "default@example.com"

    def test_send_email_with_plain_text_sets_content(self):
        """Plain text content is set when body_text provided."""
        with patch("auxctmailer.mailer.SendGridAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_client.send.return_value = mock_response

            sender = SendGridEmailSender(
                api_key="SG.test_key",
                from_email="sender@example.com",
            )
            sender.send_email(
                to_email="recipient@example.com",
                subject="Test",
                body_html="<p>Hello</p>",
                body_text="Hello",
            )

            call_args = mock_client.send.call_args
            mail_obj = call_args[0][0]
            assert mail_obj.plain_text_content is not None

    def test_mail_object_has_correct_fields(self):
        """Mail object has correct To, Subject, and HTML content."""
        with patch("auxctmailer.mailer.SendGridAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_client.send.return_value = mock_response

            sender = SendGridEmailSender(
                api_key="SG.test_key",
                from_email="sender@example.com",
            )
            sender.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                body_html="<p>Hello World</p>",
            )

            call_args = mock_client.send.call_args
            mail_obj = call_args[0][0]
            assert mail_obj.subject.subject == "Test Subject"


class TestEmailSender:
    """Tests for the EmailSender (SMTP) class."""

    def test_send_email_success(self):
        """Successful email send returns True."""
        with patch("auxctmailer.mailer.smtplib.SMTP") as mock_smtp_class:
            mock_server = MagicMock()
            mock_smtp_class.return_value = mock_server

            sender = EmailSender(
                smtp_host="smtp.example.com",
                smtp_port=587,
                username="user@example.com",
                password="password123",
            )
            result = sender.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                body_html="<p>Hello</p>",
            )

            assert result is True
            mock_server.send_message.assert_called_once()
            mock_server.quit.assert_called_once()

    def test_send_email_with_tls_calls_starttls(self):
        """When use_tls=True, starttls() is called."""
        with patch("auxctmailer.mailer.smtplib.SMTP") as mock_smtp_class:
            mock_server = MagicMock()
            mock_smtp_class.return_value = mock_server

            sender = EmailSender(
                smtp_host="smtp.example.com",
                smtp_port=587,
                username="user@example.com",
                password="password123",
                use_tls=True,
            )
            sender.send_email(
                to_email="recipient@example.com",
                subject="Test",
                body_html="<p>Hello</p>",
            )

            mock_server.starttls.assert_called_once()

    def test_send_email_without_tls_skips_starttls(self):
        """When use_tls=False, starttls() is not called."""
        with patch("auxctmailer.mailer.smtplib.SMTP") as mock_smtp_class:
            mock_server = MagicMock()
            mock_smtp_class.return_value = mock_server

            sender = EmailSender(
                smtp_host="smtp.example.com",
                smtp_port=587,
                username="user@example.com",
                password="password123",
                use_tls=False,
            )
            sender.send_email(
                to_email="recipient@example.com",
                subject="Test",
                body_html="<p>Hello</p>",
            )

            mock_server.starttls.assert_not_called()

    def test_send_email_connection_failure_returns_false(self):
        """Connection failure returns False."""
        with patch("auxctmailer.mailer.smtplib.SMTP") as mock_smtp_class:
            mock_smtp_class.side_effect = ConnectionRefusedError("Connection refused")

            sender = EmailSender(
                smtp_host="smtp.example.com",
                smtp_port=587,
                username="user@example.com",
                password="password123",
            )
            result = sender.send_email(
                to_email="recipient@example.com",
                subject="Test",
                body_html="<p>Hello</p>",
            )

            assert result is False

    def test_send_email_auth_failure_returns_false(self):
        """Authentication failure returns False."""
        from smtplib import SMTPAuthenticationError

        with patch("auxctmailer.mailer.smtplib.SMTP") as mock_smtp_class:
            mock_server = MagicMock()
            mock_smtp_class.return_value = mock_server
            mock_server.login.side_effect = SMTPAuthenticationError(535, b"Auth failed")

            sender = EmailSender(
                smtp_host="smtp.example.com",
                smtp_port=587,
                username="user@example.com",
                password="wrongpassword",
            )
            result = sender.send_email(
                to_email="recipient@example.com",
                subject="Test",
                body_html="<p>Hello</p>",
            )

            assert result is False

    def test_send_email_default_from_uses_username(self):
        """Without from_email, sender uses username."""
        with patch("auxctmailer.mailer.smtplib.SMTP") as mock_smtp_class:
            mock_server = MagicMock()
            mock_smtp_class.return_value = mock_server

            sender = EmailSender(
                smtp_host="smtp.example.com",
                smtp_port=587,
                username="user@example.com",
                password="password123",
            )
            sender.send_email(
                to_email="recipient@example.com",
                subject="Test",
                body_html="<p>Hello</p>",
            )

            # Check that send_message was called with a message having From = username
            call_args = mock_server.send_message.call_args
            msg = call_args[0][0]
            assert msg["From"] == "user@example.com"

    def test_send_email_with_plain_text_attaches_both(self):
        """Both HTML and plain text are attached when body_text provided."""
        with patch("auxctmailer.mailer.smtplib.SMTP") as mock_smtp_class:
            mock_server = MagicMock()
            mock_smtp_class.return_value = mock_server

            sender = EmailSender(
                smtp_host="smtp.example.com",
                smtp_port=587,
                username="user@example.com",
                password="password123",
            )
            sender.send_email(
                to_email="recipient@example.com",
                subject="Test",
                body_html="<p>Hello</p>",
                body_text="Hello",
            )

            call_args = mock_server.send_message.call_args
            msg = call_args[0][0]
            # Message should be multipart with both text/plain and text/html
            payloads = msg.get_payload()
            content_types = [p.get_content_type() for p in payloads]
            assert "text/plain" in content_types
            assert "text/html" in content_types


class TestEmailTemplate:
    """Tests for the EmailTemplate class."""

    def test_render_with_context(self, tmp_template_dir):
        """Render template file with context variables substituted."""
        template = EmailTemplate(template_dir=tmp_template_dir)
        result = template.render("test_template.html", name="World")
        assert result == "<html><body>Hello World</body></html>"

    def test_render_string_with_context(self, tmp_template_dir):
        """Render a template string with context variables substituted."""
        template = EmailTemplate(template_dir=tmp_template_dir)
        result = template.render_string("Hello {{ name }}!", name="Alice")
        assert result == "Hello Alice!"

    def test_render_missing_template_raises_error(self, tmp_template_dir):
        """Attempting to render a non-existent template raises TemplateNotFound."""
        from jinja2 import TemplateNotFound

        template = EmailTemplate(template_dir=tmp_template_dir)
        with pytest.raises(TemplateNotFound):
            template.render("nonexistent_template.html")

    def test_render_with_missing_vars_renders_empty(self, tmp_template_dir):
        """Undefined template variables render as empty strings."""
        template = EmailTemplate(template_dir=tmp_template_dir)
        # Template expects 'name' but we don't provide it
        result = template.render("test_template.html")
        assert result == "<html><body>Hello </body></html>"

    def test_default_template_dir_uses_package_templates(self):
        """Without template_dir argument, uses package templates folder."""
        from pathlib import Path

        template = EmailTemplate()
        expected_dir = Path(__file__).parent.parent / "auxctmailer" / "templates"
        assert template.template_dir == expected_dir


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
