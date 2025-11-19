"""
Test script for Email Service
Run this to verify email functionality
Note: Requires SMTP credentials in .env file
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from services.EmailService import EmailService
from agents.BookingAgent import BookingAgent
from database.Database import get_session
from database.models import Appointment


def test_email_configuration():
    """Test email service configuration"""
    print("Testing email configuration...")
    email = EmailService()
    
    if email.is_configured:
        print(f"  ✓ Email service configured")
        print(f"    SMTP Host: {email.smtp_host}")
        print(f"    SMTP Port: {email.smtp_port}")
        print(f"    From Email: {email.from_email}")
    else:
        print(f"  ⚠ Email service not configured")
        print(f"    Please set SMTP_USER and SMTP_PASSWORD in .env file")
        print(f"    Example:")
        print(f"      SMTP_HOST=smtp.gmail.com")
        print(f"      SMTP_PORT=587")
        print(f"      SMTP_USER=your-email@gmail.com")
        print(f"      SMTP_PASSWORD=your-app-password")
        return False
    
    return True


def test_email_connection():
    """Test SMTP connection"""
    print("\nTesting SMTP connection...")
    email = EmailService()
    
    result = email.test_email_connection()
    
    if result["success"]:
        print(f"  ✓ {result['message']}")
        return True
    else:
        print(f"  ✗ {result['message']}")
        print(f"    Note: This test requires valid SMTP credentials")
        return False


def test_create_email_body():
    """Test creating email body"""
    print("\nTesting email body creation...")
    email = EmailService()
    booking = BookingAgent()
    
    # Get an appointment
    db = get_session()
    try:
        appointment = db.query(Appointment).filter(
            Appointment.status.in_(['pending', 'confirmed'])
        ).first()
        
        if not appointment:
            print(f"  ✗ No appointments found to test")
            return False
        
        from database.models import Student, Advisor
        student = db.query(Student).filter(Student.asu_id == appointment.student_id).first()
        advisor = db.query(Advisor).filter(Advisor.advisor_id == appointment.advisor_id).first()
        
        if not student or not advisor:
            print(f"  ✗ Student or advisor not found")
            return False
        
        plain_text, html_text = email.create_appointment_email_body(appointment, student, advisor)
        
        print(f"  ✓ Email body created")
        print(f"    Plain text length: {len(plain_text)} characters")
        print(f"    HTML length: {len(html_text)} characters")
        print(f"    Preview:")
        print(f"    {plain_text[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False
    finally:
        db.close()


def test_send_test_email():
    """Test sending a test email (optional, requires real email)"""
    print("\nTesting send email (optional)...")
    email = EmailService()
    
    if not email.is_configured:
        print(f"  ⚠ Skipped - Email not configured")
        return None
    
    # Ask user if they want to send a test email
    print(f"  Note: This will send a real email to the test student")
    print(f"  To test, uncomment the code below and provide a test email address")
    
    # Uncomment below to actually send a test email
    # test_email = "test@example.com"  # Change this to your test email
    # result = email._send_email(
    #     test_email,
    #     "Test Email from ASU Academic Assistant",
    #     "This is a test email to verify SMTP configuration."
    # )
    # 
    # if result["success"]:
    #     print(f"  ✓ Test email sent successfully")
    #     return True
    # else:
    #     print(f"  ✗ Failed to send test email: {result['message']}")
    #     return False
    
    print(f"  ⚠ Test email sending skipped (requires manual activation)")
    return None


def test_send_appointment_confirmation():
    """Test sending appointment confirmation email"""
    print("\nTesting send appointment confirmation...")
    email = EmailService()
    booking = BookingAgent()
    
    if not email.is_configured:
        print(f"  ⚠ Skipped - Email not configured")
        return None
    
    # Get an appointment
    db = get_session()
    try:
        appointment = db.query(Appointment).filter(
            Appointment.status.in_(['pending', 'confirmed']),
            Appointment.confirmation_email_sent == False
        ).first()
        
        if not appointment:
            print(f"  ⚠ No appointments found that need confirmation")
            return None
        
        print(f"  Attempting to send confirmation for appointment: {appointment.appointment_id}")
        print(f"  Note: This will send a real email if SMTP is properly configured")
        
        # Uncomment to actually send
        # result = email.send_appointment_confirmation(appointment)
        # 
        # if result["success"]:
        #     print(f"  ✓ Confirmation email sent successfully")
        #     return True
        # else:
        #     print(f"  ✗ Failed to send confirmation: {result['message']}")
        #     return False
        
        print(f"  ⚠ Email sending skipped (requires manual activation)")
        return None
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False
    finally:
        db.close()


def main():
    """Run all email tests"""
    print("=" * 50)
    print("Email Service Test Suite")
    print("=" * 50)
    print("\nNote: Some tests require SMTP credentials in .env file")
    print("=" * 50)
    
    results = []
    
    config_result = test_email_configuration()
    results.append(("Email Configuration", config_result))
    
    if config_result:
        results.append(("SMTP Connection", test_email_connection()))
        results.append(("Create Email Body", test_create_email_body()))
        
        # Optional tests (won't fail if skipped)
        test_email_result = test_send_test_email()
        if test_email_result is not None:
            results.append(("Send Test Email", test_email_result))
        
        confirmation_result = test_send_appointment_confirmation()
        if confirmation_result is not None:
            results.append(("Send Confirmation", confirmation_result))
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    for test_name, result in results:
        if result is None:
            status = "⚠ SKIPPED"
        elif result:
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
        print(f"{test_name}: {status}")
    
    # Only count non-skipped tests
    non_skipped = [r for r in results if r[1] is not None]
    all_passed = all(result for _, result in non_skipped) if non_skipped else False
    
    if all_passed and non_skipped:
        print("\n✓ All email tests passed!")
    elif not non_skipped:
        print("\n⚠ Email tests skipped - configure SMTP in .env to test")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
    
    print("\nTo configure email service, add to .env file:")
    print("  SMTP_HOST=smtp.gmail.com")
    print("  SMTP_PORT=587")
    print("  SMTP_USER=your-email@gmail.com")
    print("  SMTP_PASSWORD=your-app-password")
    
    return all_passed


if __name__ == "__main__":
    main()


