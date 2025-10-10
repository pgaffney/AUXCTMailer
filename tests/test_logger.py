"""Tests for logger module."""

import logging
import pytest
from pathlib import Path
from auxctmailer.logger import setup_logger, get_logger


class TestLogger:
    """Tests for logging configuration."""

    def test_setup_logger_default(self):
        """Test setting up logger with default settings."""
        logger = setup_logger("test_logger_1")
        assert logger.name == "test_logger_1"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_setup_logger_with_level(self):
        """Test setting up logger with custom log level."""
        logger = setup_logger("test_logger_2", level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_setup_logger_with_file(self, tmp_path):
        """Test setting up logger with file output."""
        log_file = tmp_path / "test.log"
        logger = setup_logger("test_logger_3", log_file=str(log_file))

        # Log a test message
        logger.info("Test message")

        # Verify file was created and contains message
        assert log_file.exists()
        log_content = log_file.read_text()
        assert "Test message" in log_content
        assert "INFO" in log_content

    def test_get_logger(self):
        """Test getting existing logger."""
        # Setup a logger
        setup_logger("test_logger_4", level=logging.WARNING)

        # Get the same logger
        logger = get_logger("test_logger_4")
        assert logger.name == "test_logger_4"
        assert logger.level == logging.WARNING

    def test_logger_no_duplicates(self):
        """Test that re-setup doesn't create duplicate handlers."""
        logger1 = setup_logger("test_logger_5")
        handler_count_1 = len(logger1.handlers)

        # Setup again
        logger2 = setup_logger("test_logger_5")
        handler_count_2 = len(logger2.handlers)

        # Should have same number of handlers
        assert handler_count_1 == handler_count_2

    def test_logger_levels(self, tmp_path):
        """Test different log levels work correctly."""
        log_file = tmp_path / "levels.log"
        logger = setup_logger("test_logger_6", level=logging.INFO, log_file=str(log_file))

        # Log at different levels
        logger.debug("Debug message")  # Should not appear
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        log_content = log_file.read_text()
        assert "Debug message" not in log_content  # Below threshold
        assert "Info message" in log_content
        assert "Warning message" in log_content
        assert "Error message" in log_content
