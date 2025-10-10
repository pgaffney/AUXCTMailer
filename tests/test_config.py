"""Tests for config module."""

import pytest
import os
from auxctmailer.config import EmailConfig, load_email_config
from auxctmailer.exceptions import ConfigError


class TestEmailConfig:
    """Tests for EmailConfig class."""

    def test_sendgrid_config_valid(self):
        """Test valid SendGrid configuration."""
        config = EmailConfig(
            provider='sendgrid',
            from_email='test@example.com',
            sendgrid_api_key='SG.test_key'
        )
        config.validate()  # Should not raise

    def test_sendgrid_config_missing_api_key(self):
        """Test SendGrid config validation fails without API key."""
        config = EmailConfig(
            provider='sendgrid',
            from_email='test@example.com'
        )
        with pytest.raises(ConfigError, match="SENDGRID_API_KEY is required"):
            config.validate()

    def test_sendgrid_config_missing_from_email(self):
        """Test SendGrid config validation fails without from_email."""
        config = EmailConfig(
            provider='sendgrid',
            from_email='',
            sendgrid_api_key='SG.test_key'
        )
        with pytest.raises(ConfigError, match="FROM_EMAIL is required"):
            config.validate()

    def test_smtp_config_valid(self):
        """Test valid SMTP configuration."""
        config = EmailConfig(
            provider='smtp',
            from_email='test@example.com',
            smtp_host='smtp.gmail.com',
            smtp_port=587,
            smtp_user='user@example.com',
            smtp_password='password123',
            smtp_use_tls=True
        )
        config.validate()  # Should not raise

    def test_smtp_config_defaults_from_email_to_smtp_user(self):
        """Test SMTP config defaults from_email to smtp_user."""
        config = EmailConfig(
            provider='smtp',
            from_email='',  # Empty
            smtp_host='smtp.gmail.com',
            smtp_user='user@example.com',
            smtp_password='password123'
        )
        config.validate()
        assert config.from_email == 'user@example.com'

    def test_smtp_config_missing_host(self):
        """Test SMTP config validation fails without host."""
        config = EmailConfig(
            provider='smtp',
            from_email='test@example.com',
            smtp_user='user@example.com',
            smtp_password='password123'
        )
        with pytest.raises(ConfigError, match="SMTP_HOST"):
            config.validate()

    def test_smtp_config_missing_user(self):
        """Test SMTP config validation fails without user."""
        config = EmailConfig(
            provider='smtp',
            from_email='test@example.com',
            smtp_host='smtp.gmail.com',
            smtp_password='password123'
        )
        with pytest.raises(ConfigError, match="SMTP_USER"):
            config.validate()

    def test_smtp_config_missing_password(self):
        """Test SMTP config validation fails without password."""
        config = EmailConfig(
            provider='smtp',
            from_email='test@example.com',
            smtp_host='smtp.gmail.com',
            smtp_user='user@example.com'
        )
        with pytest.raises(ConfigError, match="SMTP_PASSWORD"):
            config.validate()

    def test_unknown_provider(self):
        """Test validation fails for unknown provider."""
        config = EmailConfig(
            provider='unknown',
            from_email='test@example.com'
        )
        with pytest.raises(ConfigError, match="Unknown email provider"):
            config.validate()


class TestLoadEmailConfig:
    """Tests for load_email_config function."""

    def test_load_sendgrid_config(self, monkeypatch):
        """Test loading SendGrid config from environment."""
        monkeypatch.setenv('EMAIL_PROVIDER', 'sendgrid')
        monkeypatch.setenv('SENDGRID_API_KEY', 'SG.test_key')
        monkeypatch.setenv('FROM_EMAIL', 'test@example.com')

        config = load_email_config()
        assert config.provider == 'sendgrid'
        assert config.from_email == 'test@example.com'
        assert config.sendgrid_api_key == 'SG.test_key'

    def test_load_smtp_config(self, monkeypatch):
        """Test loading SMTP config from environment."""
        monkeypatch.setenv('EMAIL_PROVIDER', 'smtp')
        monkeypatch.setenv('SMTP_HOST', 'smtp.gmail.com')
        monkeypatch.setenv('SMTP_PORT', '587')
        monkeypatch.setenv('SMTP_USER', 'user@example.com')
        monkeypatch.setenv('SMTP_PASSWORD', 'password123')
        monkeypatch.setenv('SMTP_USE_TLS', 'true')
        monkeypatch.setenv('FROM_EMAIL', 'from@example.com')

        config = load_email_config()
        assert config.provider == 'smtp'
        assert config.smtp_host == 'smtp.gmail.com'
        assert config.smtp_port == 587
        assert config.smtp_user == 'user@example.com'
        assert config.smtp_password == 'password123'
        assert config.smtp_use_tls is True
        assert config.from_email == 'from@example.com'

    def test_load_config_defaults(self, monkeypatch):
        """Test default values are applied."""
        # Clear all env vars
        for key in ['EMAIL_PROVIDER', 'FROM_EMAIL', 'SENDGRID_API_KEY',
                    'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD']:
            monkeypatch.delenv(key, raising=False)

        # Set only required vars for sendgrid
        monkeypatch.setenv('SENDGRID_API_KEY', 'SG.test_key')
        monkeypatch.setenv('FROM_EMAIL', 'test@example.com')

        config = load_email_config()
        assert config.provider == 'sendgrid'  # Default
        assert config.smtp_port == 587  # Default
        assert config.smtp_use_tls is True  # Default

    def test_load_config_invalid_raises_error(self, monkeypatch):
        """Test loading invalid config raises ConfigError."""
        monkeypatch.setenv('EMAIL_PROVIDER', 'sendgrid')
        monkeypatch.setenv('FROM_EMAIL', 'test@example.com')
        # Explicitly clear SENDGRID_API_KEY
        monkeypatch.delenv('SENDGRID_API_KEY', raising=False)

        with pytest.raises(ConfigError, match="SENDGRID_API_KEY is required"):
            load_email_config()

    def test_smtp_use_tls_parsing(self, monkeypatch):
        """Test SMTP_USE_TLS environment variable parsing."""
        base_env = {
            'EMAIL_PROVIDER': 'smtp',
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_USER': 'user@example.com',
            'SMTP_PASSWORD': 'password123',
        }

        # Test 'true'
        for key, val in base_env.items():
            monkeypatch.setenv(key, val)
        monkeypatch.setenv('SMTP_USE_TLS', 'true')
        config = load_email_config()
        assert config.smtp_use_tls is True

        # Test '1'
        monkeypatch.setenv('SMTP_USE_TLS', '1')
        config = load_email_config()
        assert config.smtp_use_tls is True

        # Test 'false'
        monkeypatch.setenv('SMTP_USE_TLS', 'false')
        config = load_email_config()
        assert config.smtp_use_tls is False

        # Test '0'
        monkeypatch.setenv('SMTP_USE_TLS', '0')
        config = load_email_config()
        assert config.smtp_use_tls is False
