"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import importlib


@pytest.fixture
def fixtures_dir():
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_training_csv(fixtures_dir):
    """Return path to sample training CSV."""
    return str(fixtures_dir / "sample_training.csv")


@pytest.fixture
def sample_email_csv(fixtures_dir):
    """Return path to sample email CSV."""
    return str(fixtures_dir / "sample_email.csv")


@pytest.fixture
def sample_units_csv(fixtures_dir):
    """Return path to sample units CSV."""
    return str(fixtures_dir / "sample_units.csv")


@pytest.fixture
def sample_courses_csv(fixtures_dir):
    """Return path to sample courses CSV."""
    return str(fixtures_dir / "sample_courses.csv")


@pytest.fixture
def mock_smtp():
    """Return a mock SMTP connection for testing email sending."""
    return MagicMock()


@pytest.fixture
def mock_sendgrid_client():
    """Return a mock SendGrid client for testing email sending."""
    return MagicMock()


@pytest.fixture
def mock_sendgrid_api():
    """Patch SendGrid API at module level and reload dependent modules.

    Yields a mock client instance with send() returning 202 status.
    Use this fixture when testing code that sends emails via SendGrid.
    """
    with patch('sendgrid.SendGridAPIClient') as mock_sg_client:
        mock_client_instance = MagicMock()
        mock_sg_client.return_value = mock_client_instance
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_client_instance.send.return_value = mock_response

        # Reload modules to pick up the patched SendGridAPIClient
        import auxctmailer.mailer
        import auxctmailer.main
        importlib.reload(auxctmailer.mailer)
        importlib.reload(auxctmailer.main)

        yield mock_client_instance


@pytest.fixture
def sample_member_data():
    """Return sample member data dict for testing."""
    return {
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'member_num': '1234567',
    }


@pytest.fixture
def tmp_template_dir(tmp_path):
    """Return a temporary directory containing test_template.html."""
    template_file = tmp_path / "test_template.html"
    template_file.write_text("<html><body>Hello {{ name }}</body></html>")
    return str(tmp_path)
