"""Custom exception classes for AUXCTMailer."""


class AUXCTMailerError(Exception):
    """Base exception for all AUXCTMailer errors."""
    pass


class MemberDataError(AUXCTMailerError):
    """Exception raised for errors in member data loading or processing."""
    pass


class EmailSendError(AUXCTMailerError):
    """Exception raised when email sending fails."""
    pass


class TemplateError(AUXCTMailerError):
    """Exception raised for template rendering errors."""
    pass


class ConfigError(AUXCTMailerError):
    """Exception raised for configuration errors."""
    pass
