"""
Booking Agent
Handles appointment booking, calendar updates, and appointment management
"""

import sys
from pathlib import Path
import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.Database import get_session
from database.models import Appointment, Student, Advisor
from services.CalendarService import CalendarService


class BookingAgent:
    """Handles appointment booking and management"""
    
    def __init__(self):
        """Initialize Booking Agent"""
        self.calendar_service = CalendarService()
    
    def get_available_slots(self, advisor_id: str, start_date: date, end_date: date) -> List[datetime]:
        """
        Get available slots for an advisor within a date range
        
        Args:
            advisor_id: Advisor email/ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of available datetime slots
        """
        return self.calendar_service.get_available_slots(advisor_id, start_date, end_date)
    
    def book_appointment(self, student_id: str, advisor_id: str, slot_datetime: datetime, reason: Optional[str] = None) -> Dict:
        """
        Book an appointment
        
        Args:
            student_id: Student ASU ID
            advisor_id: Advisor email/ID
            slot_datetime: Datetime of the appointment slot
            reason: Optional reason for the appointment
            
        Returns:
            Dictionary with:
            - success: bool
            - appointment: Appointment object if successful, None otherwise
            - message: str (error message if failed)
        """
        db = get_session()
        try:
            # Validate student exists
            student = db.query(Student).filter(Student.asu_id == student_id).first()
            if not student:
                return {
                    "success": False,
                    "appointment": None,
                    "message": "Student not found"
                }
            
            # Validate advisor exists
            advisor = db.query(Advisor).filter(Advisor.advisor_id == advisor_id).first()
            if not advisor:
                return {
                    "success": False,
                    "appointment": None,
                    "message": "Advisor not found"
                }
            
            # Check if slot is available
            if not self.calendar_service.check_slot_availability(advisor_id, slot_datetime):
                return {
                    "success": False,
                    "appointment": None,
                    "message": "This time slot is no longer available. Please select another time."
                }
            
            # Check if slot is in the past
            if slot_datetime < datetime.now():
                return {
                    "success": False,
                    "appointment": None,
                    "message": "Cannot book appointments in the past"
                }
            
            # Check if student already has an appointment at this time
            # Normalize datetime to remove microseconds for exact comparison
            slot_normalized = slot_datetime.replace(microsecond=0)
            
            existing = db.query(Appointment).filter(
                Appointment.student_id == student_id,
                Appointment.slot_datetime == slot_normalized,
                Appointment.status.in_(['pending', 'confirmed'])
            ).first()
            
            if existing:
                existing_time = existing.slot_datetime.strftime("%A, %B %d, %Y at %I:%M %p")
                return {
                    "success": False,
                    "appointment": None,
                    "message": f"You already have a {existing.status} appointment scheduled on {existing_time}. Please select a different time slot."
                }
            
            # Create appointment
            appointment_id = str(uuid.uuid4())
            appointment = Appointment(
                appointment_id=appointment_id,
                student_id=student_id,
                advisor_id=advisor_id,
                slot_datetime=slot_datetime,
                status='BOOKED',
                confirmation_email_sent=False,
                reason=reason
            )
            
            db.add(appointment)
            
            # Mark slot as booked in calendar
            self.calendar_service.mark_slot_unavailable(advisor_id, slot_datetime, "booked")
            
            db.commit()
            db.refresh(appointment)
            
            return {
                "success": True,
                "appointment": appointment,
                "message": "Appointment booked successfully"
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "appointment": None,
                "message": f"Error booking appointment: {str(e)}"
            }
        finally:
            db.close()
    
    def cancel_appointment(self, appointment_id: str, student_id: str) -> Dict:
        """
        Cancel an appointment
        
        Args:
            appointment_id: Appointment UUID
            student_id: Student ASU ID (for verification)
            
        Returns:
            Dictionary with success status and message
        """
        db = get_session()
        try:
            appointment = db.query(Appointment).filter(
                Appointment.appointment_id == appointment_id,
                Appointment.student_id == student_id
            ).first()
            
            if not appointment:
                return {
                    "success": False,
                    "message": "Appointment not found or you don't have permission to cancel it"
                }
            
            if appointment.status == 'cancelled':
                return {
                    "success": False,
                    "message": "Appointment is already cancelled"
                }
            
            # Update appointment status
            appointment.status = 'cancelled'
            
            # Mark slot as available again
            self.calendar_service.mark_slot_available(appointment.advisor_id, appointment.slot_datetime)
            
            db.commit()
            
            return {
                "success": True,
                "message": "Appointment cancelled successfully"
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error cancelling appointment: {str(e)}"
            }
        finally:
            db.close()
    
    def confirm_appointment(self, appointment_id: str) -> Dict:
        """
        Confirm an appointment (change status from pending to confirmed)
        
        Args:
            appointment_id: Appointment UUID
            
        Returns:
            Dictionary with success status and message
        """
        db = get_session()
        try:
            appointment = db.query(Appointment).filter(
                Appointment.appointment_id == appointment_id
            ).first()
            
            if not appointment:
                return {
                    "success": False,
                    "message": "Appointment not found"
                }
            
            appointment.status = 'confirmed'
            db.commit()
            db.refresh(appointment)
            
            return {
                "success": True,
                "message": "Appointment confirmed",
                "appointment": {
                    "appointment_id": appointment.appointment_id,
                    "student_id": appointment.student_id,
                    "advisor_id": appointment.advisor_id,
                    "slot_datetime": appointment.slot_datetime,
                    "status": appointment.status,
                    "confirmation_email_sent": appointment.confirmation_email_sent
                }
            }
            
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"Error confirming appointment: {str(e)}"
            }
        finally:
            db.close()
    
    def get_student_appointments(self, student_id: str, include_cancelled: bool = False) -> List[Appointment]:
        """
        Get all appointments for a student
        
        Args:
            student_id: Student ASU ID
            include_cancelled: Whether to include cancelled appointments
            
        Returns:
            List of Appointment objects
        """
        db = get_session()
        try:
            query = db.query(Appointment).filter(Appointment.student_id == student_id)
            
            if not include_cancelled:
                query = query.filter(Appointment.status != 'cancelled')
            
            appointments = query.order_by(Appointment.slot_datetime.asc()).all()
            return appointments
            
        except Exception as e:
            print(f"Error getting student appointments: {e}")
            return []
        finally:
            db.close()
    
    def get_advisor_appointments(self, advisor_id: str, start_date: date, end_date: date) -> List[Appointment]:
        """
        Get all appointments for an advisor within a date range
        
        Args:
            advisor_id: Advisor email/ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of Appointment objects
        """
        db = get_session()
        try:
            appointments = db.query(Appointment).filter(
                Appointment.advisor_id == advisor_id,
                Appointment.slot_datetime >= datetime.combine(start_date, datetime.min.time()),
                Appointment.slot_datetime <= datetime.combine(end_date, datetime.max.time()),
                Appointment.status.in_(['pending', 'confirmed'])
            ).order_by(Appointment.slot_datetime.asc()).all()
            
            return appointments
            
        except Exception as e:
            print(f"Error getting advisor appointments: {e}")
            return []
        finally:
            db.close()
    
    def get_appointment_details(self, appointment_id: str) -> Optional[Appointment]:
        """
        Get appointment details by ID
        
        Args:
            appointment_id: Appointment UUID
            
        Returns:
            Appointment object if found, None otherwise
        """
        db = get_session()
        try:
            appointment = db.query(Appointment).filter(
                Appointment.appointment_id == appointment_id
            ).first()
            
            return appointment
            
        except Exception as e:
            print(f"Error getting appointment details: {e}")
            return None
        finally:
            db.close()
    
    def mark_confirmation_sent(self, appointment_id: str) -> bool:
        """
        Mark that confirmation email has been sent
        
        Args:
            appointment_id: Appointment UUID
            
        Returns:
            True if successful, False otherwise
        """
        db = get_session()
        try:
            appointment = db.query(Appointment).filter(
                Appointment.appointment_id == appointment_id
            ).first()
            
            if appointment:
                appointment.confirmation_email_sent = True
                db.commit()
                return True
            
            return False
            
        except Exception as e:
            db.rollback()
            print(f"Error marking confirmation sent: {e}")
            return False
        finally:
            db.close()
    
    def format_appointment_summary(self, appointment: Appointment) -> str:
        """
        Format appointment details for display
        
        Args:
            appointment: Appointment object
            
        Returns:
            Formatted string with appointment details
        """
        db = get_session()
        try:
            student = db.query(Student).filter(Student.asu_id == appointment.student_id).first()
            advisor = db.query(Advisor).filter(Advisor.advisor_id == appointment.advisor_id).first()
            
            formatted_date = appointment.slot_datetime.strftime("%A, %B %d, %Y")
            formatted_time = appointment.slot_datetime.strftime("%I:%M %p")
            
            summary = f"""
Appointment Details:
- Appointment ID: {appointment.appointment_id}
- Student: {student.name if student else 'Unknown'} ({appointment.student_id})
- Advisor: {advisor.name if advisor else 'Unknown'}
- Date: {formatted_date}
- Time: {formatted_time}
- Status: {appointment.status.title()}
"""
            
            if appointment.reason:
                summary += f"- Reason: {appointment.reason}\n"
            
            return summary.strip()
            
        except Exception as e:
            return f"Error formatting appointment: {str(e)}"
        finally:
            db.close()

