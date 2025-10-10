"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path


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
