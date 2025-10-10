"""Configuration management for AUXCTMailer."""

import os
from typing import Optional
from dataclasses import dataclass

from auxctmailer.exceptions import ConfigError


@dataclass
class EmailConfig:
    """Email provider configuration."""
    provider: str
    from_email: str

    # SendGrid specific
    sendgrid_api_key: Optional[str] = None

    # SMTP specific
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True

    def validate(self) -> None:
        """Validate configuration based on provider.

        Raises:
            ConfigError: If required configuration is missing
        """
        if self.provider == 'sendgrid':
            if not self.sendgrid_api_key:
                raise ConfigError("SENDGRID_API_KEY is required for SendGrid provider")
            if not self.from_email:
                raise ConfigError("FROM_EMAIL is required for SendGrid provider")
        elif self.provider == 'smtp':
            if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
                raise ConfigError("SMTP_HOST, SMTP_USER, and SMTP_PASSWORD are required for SMTP provider")
            # FROM_EMAIL defaults to SMTP_USER if not specified
            if not self.from_email:
                self.from_email = self.smtp_user
        else:
            raise ConfigError(f"Unknown email provider: {self.provider}. Must be 'sendgrid' or 'smtp'")


def load_email_config() -> EmailConfig:
    """Load email configuration from environment variables.

    Returns:
        EmailConfig instance

    Raises:
        ConfigError: If configuration is invalid
    """
    provider = os.getenv('EMAIL_PROVIDER', 'sendgrid').lower()
    from_email = os.getenv('FROM_EMAIL', '')

    config = EmailConfig(
        provider=provider,
        from_email=from_email,
        sendgrid_api_key=os.getenv('SENDGRID_API_KEY'),
        smtp_host=os.getenv('SMTP_HOST', 'smtp.gmail.com'),
        smtp_port=int(os.getenv('SMTP_PORT', '587')),
        smtp_user=os.getenv('SMTP_USER'),
        smtp_password=os.getenv('SMTP_PASSWORD'),
        smtp_use_tls=os.getenv('SMTP_USE_TLS', 'true').lower() in ('true', '1', 'yes'),
    )

    config.validate()
    return config
