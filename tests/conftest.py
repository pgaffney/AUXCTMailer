"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock


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
