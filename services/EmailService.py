"""
Email Service
Handles sending appointment confirmation emails via SMTP
"""

import sys
from pathlib import Path
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from database.Database import get_session
from database.models import Appointment, Student, Advisor

load_dotenv()


class EmailService:
    """Handles email sending for appointment confirmations"""
    
    def __init__(self):
        """Initialize Email Service with SMTP configuration"""
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("SMTP_USER", "")
        
        # Check if email is configured
        self.is_configured = bool(self.smtp_user and self.smtp_password)
    
    def _create_email_message(self, to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> MIMEMultipart:
        """
        Create an email message
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: Optional HTML body
            
        Returns:
            MIMEMultipart message object
        """
        msg = MIMEMultipart('alternative')
        msg['From'] = self.from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add plain text part
        text_part = MIMEText(body_text, 'plain')
        msg.attach(text_part)
        
        # Add HTML part if provided
        if body_html:
            html_part = MIMEText(body_html, 'html')
            msg.attach(html_part)
        
        return msg
    
    def _send_email(self, to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> Dict:
        """
        Send an email via SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: Optional HTML body
            
        Returns:
            Dictionary with success status and message
        """
        if not self.is_configured:
            return {
                "success": False,
                "message": "Email service not configured. Please set SMTP_USER and SMTP_PASSWORD in .env file"
            }
        
        try:
            # Create message
            msg = self._create_email_message(to_email, subject, body_text, body_html)
            
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()  # Enable TLS encryption
            server.login(self.smtp_user, self.smtp_password)
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            return {
                "success": True,
                "message": f"Email sent successfully to {to_email}"
            }
            
        except smtplib.SMTPAuthenticationError:
            return {
                "success": False,
                "message": "SMTP authentication failed. Please check your email credentials."
            }
        except smtplib.SMTPException as e:
            return {
                "success": False,
                "message": f"SMTP error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error sending email: {str(e)}"
            }
    
    def create_appointment_email_body(self, appointment: Appointment, student: Student, advisor: Advisor) -> tuple:
        """
        Create email body for appointment confirmation
        
        Args:
            appointment: Appointment object
            student: Student object
            advisor: Advisor object
            
        Returns:
            Tuple of (plain_text, html_text)
        """
        formatted_date = appointment.slot_datetime.strftime("%A, %B %d, %Y")
        formatted_time = appointment.slot_datetime.strftime("%I:%M %p")
        
        # Plain text version
        plain_text = f"""
ASU Polytechnic School - Appointment Confirmation

Dear {student.name},

Your advising appointment has been confirmed.

Appointment Details:
- Advisor: {advisor.name} ({advisor.title})
- Date: {formatted_date}
- Time: {formatted_time}
- Location: {advisor.office_location or 'Sutton Hall'}
- Advisor Email: {advisor.email}
- Advisor Phone: {advisor.phone or '480-727-1874'}

Appointment ID: {appointment.appointment_id}

Please arrive on time for your appointment. If you need to cancel or reschedule, please contact the advising office at 480-727-1874.

Best regards,
ASU Polytechnic School Advising Office
"""
        
        # HTML version
        html_text = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #8C1D40; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f9f9f9; }}
        .details {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #8C1D40; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>ASU Polytechnic School</h2>
            <h3>Appointment Confirmation</h3>
        </div>
        <div class="content">
            <p>Dear {student.name},</p>
            <p>Your advising appointment has been confirmed.</p>
            
            <div class="details">
                <h3>Appointment Details:</h3>
                <p><strong>Advisor:</strong> {advisor.name} ({advisor.title})</p>
                <p><strong>Date:</strong> {formatted_date}</p>
                <p><strong>Time:</strong> {formatted_time}</p>
                <p><strong>Location:</strong> {advisor.office_location or 'Sutton Hall'}</p>
                <p><strong>Advisor Email:</strong> {advisor.email}</p>
                <p><strong>Advisor Phone:</strong> {advisor.phone or '480-727-1874'}</p>
                <p><strong>Appointment ID:</strong> {appointment.appointment_id}</p>
            </div>
            
            <p>Please arrive on time for your appointment. If you need to cancel or reschedule, please contact the advising office at 480-727-1874.</p>
            
            <p>Best regards,<br>ASU Polytechnic School Advising Office</p>
        </div>
        <div class="footer">
            <p>This is an automated confirmation email. Please do not reply to this message.</p>
        </div>
    </div>
</body>
</html>
"""
        
        return plain_text.strip(), html_text
    
    def send_appointment_confirmation(self, appointment: Appointment) -> Dict:
        """
        Send appointment confirmation email
        
        Args:
            appointment: Appointment object
            
        Returns:
            Dictionary with success status and message
        """
        db = get_session()
        try:
            # Get student and advisor information
            student = db.query(Student).filter(Student.asu_id == appointment.student_id).first()
            advisor = db.query(Advisor).filter(Advisor.advisor_id == appointment.advisor_id).first()
            
            if not student:
                return {
                    "success": False,
                    "message": "Student not found"
                }
            
            if not advisor:
                return {
                    "success": False,
                    "message": "Advisor not found"
                }
            
            # Create email body
            plain_text, html_text = self.create_appointment_email_body(appointment, student, advisor)
            
            # Send email
            subject = f"Appointment Confirmation - {appointment.slot_datetime.strftime('%B %d, %Y')}"
            result = self._send_email(student.email, subject, plain_text, html_text)
            
            # Mark confirmation as sent if successful
            if result["success"]:
                from agents.BookingAgent import BookingAgent
                booking_agent = BookingAgent()
                booking_agent.mark_confirmation_sent(appointment.appointment_id)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error preparing confirmation email: {str(e)}"
            }
        finally:
            db.close()
    
    def send_appointment_cancellation(self, appointment: Appointment) -> Dict:
        """
        Send appointment cancellation email
        
        Args:
            appointment: Appointment object
            
        Returns:
            Dictionary with success status and message
        """
        db = get_session()
        try:
            student = db.query(Student).filter(Student.asu_id == appointment.student_id).first()
            advisor = db.query(Advisor).filter(Advisor.advisor_id == appointment.advisor_id).first()
            
            if not student or not advisor:
                return {
                    "success": False,
                    "message": "Student or advisor not found"
                }
            
            formatted_date = appointment.slot_datetime.strftime("%A, %B %d, %Y")
            formatted_time = appointment.slot_datetime.strftime("%I:%M %p")
            
            plain_text = f"""
ASU Polytechnic School - Appointment Cancellation

Dear {student.name},

Your appointment has been cancelled.

Cancelled Appointment Details:
- Advisor: {advisor.name}
- Date: {formatted_date}
- Time: {formatted_time}

If you need to reschedule, please contact the advising office at 480-727-1874 or book a new appointment through the system.

Best regards,
ASU Polytechnic School Advising Office
"""
            
            subject = f"Appointment Cancelled - {formatted_date}"
            result = self._send_email(student.email, subject, plain_text)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error sending cancellation email: {str(e)}"
            }
        finally:
            db.close()
    
    def test_email_connection(self) -> Dict:
        """
        Test email service configuration and connection
        
        Returns:
            Dictionary with test results
        """
        if not self.is_configured:
            return {
                "success": False,
                "message": "Email service not configured. Please set SMTP_USER and SMTP_PASSWORD in .env file"
            }
        
        try:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.quit()
            
            return {
                "success": True,
                "message": "Email service configured and connection successful"
            }
            
        except smtplib.SMTPAuthenticationError:
            return {
                "success": False,
                "message": "SMTP authentication failed. Please check your credentials."
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}"
            }


