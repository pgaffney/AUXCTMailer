"""Tests for mailer module."""

import pytest

from auxctmailer.mailer import EmailTemplate


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
