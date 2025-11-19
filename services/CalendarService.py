"""
Calendar Service
Handles advisor calendar slot generation, availability checking, and calendar management
"""

import sys
from pathlib import Path
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict
from dateutil import rrule

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.Database import get_session
from database.models import Advisor, AdvisorCalendar, Appointment


class CalendarService:
    """Manages advisor calendar slots and availability"""
    
    # Default working hours: 8 AM to 5 PM
    DEFAULT_START_HOUR = 8
    DEFAULT_END_HOUR = 17  # 5 PM
    
    # Slot duration in minutes
    SLOT_DURATION_MINUTES = 30
    
    def __init__(self):
        """Initialize Calendar Service"""
        pass
    
    def get_working_hours(self, advisor_id: str) -> Dict:
        """
        Get working hours for an advisor
        Currently returns default hours, but can be extended to store per-advisor hours
        
        Args:
            advisor_id: Advisor email/ID
            
        Returns:
            Dictionary with working hours configuration
        """
        # Default: Monday-Friday, 8 AM - 5 PM
        # Can be extended to store per-advisor hours in database
        return {
            "start_hour": self.DEFAULT_START_HOUR,
            "end_hour": self.DEFAULT_END_HOUR,
            "days_of_week": [0, 1, 2, 3, 4]  # Monday=0, Friday=4
        }
    
    def generate_slots_for_date(self, advisor_id: str, target_date: date) -> List[datetime]:
        """
        Generate all available time slots for an advisor on a specific date
        
        Args:
            advisor_id: Advisor email/ID
            target_date: Date to generate slots for
            
        Returns:
            List of datetime objects representing available slots
        """
        working_hours = self.get_working_hours(advisor_id)
        start_hour = working_hours["start_hour"]
        end_hour = working_hours["end_hour"]
        days_of_week = working_hours["days_of_week"]
        
        # Check if date is a working day
        if target_date.weekday() not in days_of_week:
            return []  # Weekend or non-working day
        
        slots = []
        current_time = datetime.combine(target_date, time(start_hour, 0))
        end_time = datetime.combine(target_date, time(end_hour, 0))
        
        # Generate 30-minute slots
        while current_time < end_time:
            slots.append(current_time)
            current_time += timedelta(minutes=self.SLOT_DURATION_MINUTES)
        
        return slots
    
    def generate_slots_for_date_range(self, advisor_id: str, start_date: date, end_date: date) -> List[datetime]:
        """
        Generate all available time slots for an advisor within a date range
        
        Args:
            advisor_id: Advisor email/ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of datetime objects representing available slots
        """
        all_slots = []
        current_date = start_date
        
        while current_date <= end_date:
            date_slots = self.generate_slots_for_date(advisor_id, current_date)
            all_slots.extend(date_slots)
            current_date += timedelta(days=1)
        
        return all_slots
    
    def check_slot_availability(self, advisor_id: str, slot_datetime: datetime) -> bool:
        """
        Check if a specific slot is available for booking
        
        Args:
            advisor_id: Advisor email/ID
            slot_datetime: Datetime of the slot to check
            
        Returns:
            True if available, False if booked or blocked
        """
        db = get_session()
        try:
            # Check if slot is in advisor_calendar and marked as booked/blocked
            # Normalize datetime to remove microseconds for comparison
            slot_normalized = slot_datetime.replace(microsecond=0)
            calendar_entry = db.query(AdvisorCalendar).filter(
                AdvisorCalendar.advisor_id == advisor_id,
                AdvisorCalendar.slot_datetime == slot_normalized,
                AdvisorCalendar.status.in_(['booked', 'blocked'])
            ).first()
            
            if calendar_entry:
                return False  # Slot is booked or blocked
            
            # Check if there's an appointment for this slot
            # Normalize datetime to remove microseconds for comparison
            slot_normalized = slot_datetime.replace(microsecond=0)
            appointment = db.query(Appointment).filter(
                Appointment.advisor_id == advisor_id,
                Appointment.slot_datetime == slot_normalized,
                Appointment.status.in_(['pending', 'confirmed'])
            ).first()
            
            if appointment:
                return False  # Slot has an appointment
            
            # Check if slot is in the past
            if slot_datetime < datetime.now():
                return False  # Can't book past slots
            
            return True  # Slot is available
            
        except Exception as e:
            print(f"Error checking slot availability: {e}")
            return False
        finally:
            db.close()
    
    def get_available_slots(self, advisor_id: str, start_date: date, end_date: date) -> List[datetime]:
        """
        Get all available slots for an advisor within a date range
        
        Args:
            advisor_id: Advisor email/ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of available datetime slots
        """
        # Generate all possible slots
        all_slots = self.generate_slots_for_date_range(advisor_id, start_date, end_date)
        
        # Filter to only available slots
        available_slots = [
            slot for slot in all_slots
            if self.check_slot_availability(advisor_id, slot)
        ]
        
        return available_slots
    
    def mark_slot_unavailable(self, advisor_id: str, slot_datetime: datetime, reason: str = "booked") -> bool:
        """
        Mark a slot as unavailable (booked or blocked)
        
        Args:
            advisor_id: Advisor email/ID
            slot_datetime: Datetime of the slot
            reason: 'booked' or 'blocked'
            
        Returns:
            True if successful, False otherwise
        """
        db = get_session()
        try:
            # Check if entry already exists
            existing = db.query(AdvisorCalendar).filter(
                AdvisorCalendar.advisor_id == advisor_id,
                AdvisorCalendar.slot_datetime == slot_datetime
            ).first()
            
            if existing:
                # Update existing entry
                existing.status = reason
            else:
                # Create new entry
                calendar_entry = AdvisorCalendar(
                    advisor_id=advisor_id,
                    slot_datetime=slot_datetime,
                    status=reason
                )
                db.add(calendar_entry)
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            print(f"Error marking slot unavailable: {e}")
            return False
        finally:
            db.close()
    
    def mark_slot_available(self, advisor_id: str, slot_datetime: datetime) -> bool:
        """
        Mark a slot as available (remove from calendar or mark as available)
        
        Args:
            advisor_id: Advisor email/ID
            slot_datetime: Datetime of the slot
            
        Returns:
            True if successful, False otherwise
        """
        db = get_session()
        try:
            # Remove or update calendar entry
            calendar_entry = db.query(AdvisorCalendar).filter(
                AdvisorCalendar.advisor_id == advisor_id,
                AdvisorCalendar.slot_datetime == slot_datetime
            ).first()
            
            if calendar_entry:
                if calendar_entry.status == 'blocked':
                    # If blocked, just update to available
                    calendar_entry.status = 'available'
                    db.commit()
                else:
                    # If booked, remove entry (appointment handles the booking)
                    db.delete(calendar_entry)
                    db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            print(f"Error marking slot available: {e}")
            return False
        finally:
            db.close()
    
    def get_booked_slots(self, advisor_id: str, start_date: date, end_date: date) -> List[datetime]:
        """
        Get all booked slots for an advisor within a date range
        
        Args:
            advisor_id: Advisor email/ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of booked datetime slots
        """
        db = get_session()
        try:
            # Get from appointments
            appointments = db.query(Appointment).filter(
                Appointment.advisor_id == advisor_id,
                Appointment.slot_datetime >= datetime.combine(start_date, time.min),
                Appointment.slot_datetime <= datetime.combine(end_date, time.max),
                Appointment.status.in_(['pending', 'confirmed'])
            ).all()
            
            booked_slots = [appt.slot_datetime for appt in appointments]
            
            # Also check calendar entries
            calendar_entries = db.query(AdvisorCalendar).filter(
                AdvisorCalendar.advisor_id == advisor_id,
                AdvisorCalendar.slot_datetime >= datetime.combine(start_date, time.min),
                AdvisorCalendar.slot_datetime <= datetime.combine(end_date, time.max),
                AdvisorCalendar.status == 'booked'
            ).all()
            
            for entry in calendar_entries:
                if entry.slot_datetime not in booked_slots:
                    booked_slots.append(entry.slot_datetime)
            
            return sorted(booked_slots)
            
        except Exception as e:
            print(f"Error getting booked slots: {e}")
            return []
        finally:
            db.close()
    
    def format_slot_display(self, slot_datetime: datetime) -> str:
        """
        Format a datetime slot for display
        
        Args:
            slot_datetime: Datetime slot
            
        Returns:
            Formatted string (e.g., "Monday, Feb 3, 2025 at 2:00 PM")
        """
        return slot_datetime.strftime("%A, %b %d, %Y at %I:%M %p")
    
    def format_slot_time_only(self, slot_datetime: datetime) -> str:
        """
        Format just the time portion of a slot
        
        Args:
            slot_datetime: Datetime slot
            
        Returns:
            Formatted time string (e.g., "2:00 PM")
        """
        return slot_datetime.strftime("%I:%M %p")

