"""
Test SMTP Configuration for ASU Email
This script helps you test different SMTP settings to find what works
"""

import smtplib
import os
from dotenv import load_dotenv

load_dotenv()

def test_smtp_connection(host, port, user, password):
    """Test SMTP connection with given settings"""
    try:
        print(f"\nTesting: {host}:{port}")
        print(f"User: {user}")
        
        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(user, password)
        server.quit()
        
        print(f"✓ SUCCESS! Connection works with these settings")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ Authentication failed: {e}")
        print(f"  - Check if App Password is correct")
        print(f"  - Make sure you're using App Password, not regular password")
        return False
    except smtplib.SMTPException as e:
        print(f"✗ SMTP error: {e}")
        return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def main():
    """Test different SMTP configurations"""
    print("=" * 60)
    print("ASU Email SMTP Configuration Tester")
    print("=" * 60)
    
    # Get credentials from .env
    user = os.getenv("SMTP_USER", "kbijja@asu.edu")
    password = os.getenv("SMTP_PASSWORD", "")
    
    if not password:
        print("\n⚠ No SMTP_PASSWORD found in .env file")
        print("\nPlease add to .env file:")
        print("  SMTP_USER=kbijja@asu.edu")
        print("  SMTP_PASSWORD=your-app-password-here")
        print("\nThen run this script again.")
        return
    
    print(f"\nTesting with user: {user}")
    print(f"Password: {'*' * len(password)} (hidden)")
    
    # List of SMTP servers to try
    smtp_configs = [
        ("smtp-mail.outlook.com", 587),
        ("smtp.asu.edu", 587),
        ("outlook.office365.com", 587),
        ("smtp-mail.outlook.com", 465),
        ("smtp.asu.edu", 25),
    ]
    
    print("\n" + "=" * 60)
    print("Testing SMTP Configurations...")
    print("=" * 60)
    
    success = False
    for host, port in smtp_configs:
        if test_smtp_connection(host, port, user, password):
            success = True
            print("\n" + "=" * 60)
            print("✓ WORKING CONFIGURATION FOUND!")
            print("=" * 60)
            print(f"Add these to your .env file:")
            print(f"  SMTP_HOST={host}")
            print(f"  SMTP_PORT={port}")
            print(f"  SMTP_USER={user}")
            print(f"  SMTP_PASSWORD={password}")
            print("=" * 60)
            break
    
    if not success:
        print("\n" + "=" * 60)
        print("✗ None of the configurations worked")
        print("=" * 60)
        print("\nTroubleshooting:")
        print("1. Make sure you're using an App Password (not regular password)")
        print("2. Verify 2-Step Verification is enabled on your account")
        print("3. Check if your ASU account allows SMTP access")
        print("4. Contact ASU IT support for SMTP server details")
        print("\nTo get App Password:")
        print("  - Go to: https://myaccount.microsoft.com/security")
        print("  - Click 'App passwords' or 'Advanced security options'")
        print("  - Generate a new app password")


if __name__ == "__main__":
    main()


