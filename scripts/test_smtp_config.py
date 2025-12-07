#!/usr/bin/env python3
"""Test script to verify SMTP configuration is read correctly."""

import os
from dotenv import load_dotenv

def test_smtp_config():
    """Test SMTP configuration parsing."""
    print("Testing SMTP Configuration\n" + "="*50)

    # Load environment variables
    load_dotenv()

    # Get email provider
    email_provider = os.getenv('EMAIL_PROVIDER', 'sendgrid').lower()
    print(f"Email Provider: {email_provider}")

    if email_provider != 'smtp':
        print(f"\n⚠️  EMAIL_PROVIDER is set to '{email_provider}', not 'smtp'")
        print("Set EMAIL_PROVIDER=smtp in .env to test SMTP configuration")
        return

    print("\n📧 SMTP Configuration:")
    print("-" * 50)

    # Required settings
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASSWORD')

    print(f"SMTP_HOST:     {smtp_host or '❌ NOT SET'}")
    print(f"SMTP_PORT:     {smtp_port}")
    print(f"SMTP_USER:     {smtp_user or '❌ NOT SET'}")
    print(f"SMTP_PASSWORD: {'***' + smtp_pass[-4:] if smtp_pass else '❌ NOT SET'}")

    # Optional settings
    smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() in ('true', '1', 'yes')
    from_email = os.getenv('FROM_EMAIL')

    print(f"\nSMTP_USE_TLS:  {smtp_use_tls} (from env: '{os.getenv('SMTP_USE_TLS', 'true')}')")
    print(f"FROM_EMAIL:    {from_email or f'{smtp_user} (defaulting to SMTP_USER)'}")

    # Validate
    print("\n✅ Validation:")
    print("-" * 50)

    if not all([smtp_host, smtp_user, smtp_pass]):
        print("❌ MISSING REQUIRED CONFIGURATION")
        print("   Required: SMTP_HOST, SMTP_USER, SMTP_PASSWORD")
        return False

    print("✅ All required settings present")

    # Show final configuration
    final_from_email = from_email if from_email else smtp_user
    print(f"\n📤 Final Configuration:")
    print(f"   Connect to: {smtp_host}:{smtp_port}")
    print(f"   Use TLS:    {smtp_use_tls}")
    print(f"   Login as:   {smtp_user}")
    print(f"   Send from:  {final_from_email}")

    # Port recommendations
    print(f"\n💡 Port {smtp_port} Recommendation:")
    if smtp_port == 587:
        print(f"   ✅ Port 587 with TLS={smtp_use_tls} is {'CORRECT' if smtp_use_tls else 'INCORRECT'}")
        if not smtp_use_tls:
            print("   ⚠️  Set SMTP_USE_TLS=true for port 587")
    elif smtp_port == 465:
        print(f"   ⚠️  Port 465 requires SSL (not TLS)")
        print(f"   Current setting: TLS={smtp_use_tls}")
        print(f"   Recommendation: Set SMTP_USE_TLS=false for port 465")
    elif smtp_port == 25:
        print(f"   ⚠️  Port 25 is unencrypted")
        print(f"   Recommendation: Use port 587 with TLS instead")

    return True

if __name__ == '__main__':
    success = test_smtp_config()
    exit(0 if success else 1)
