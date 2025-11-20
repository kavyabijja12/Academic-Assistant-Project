"""
Booking Conversation Agent
Manages conversational booking flow - handles natural language booking requests
"""

import sys
from pathlib import Path
import json
import re
from datetime import datetime, date, time, timedelta
from typing import Dict, Optional, List, Tuple
from dateutil import parser as date_parser

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.BookingAgent import BookingAgent
from agents.IntentClassifier import IntentClassifier
from services.CalendarService import CalendarService
from database.Database import get_session
from database.models import Advisor, Student


class BookingConversationAgent:
    """Manages conversational booking flow"""
    
    # Booking states
    STATE_INITIAL = "initial"
    STATE_NEED_PROGRAM = "need_program"
    STATE_NEED_ADVISOR = "need_advisor"
    STATE_NEED_DATE = "need_date"
    STATE_NEED_TIME = "need_time"
    STATE_NEED_REASON = "need_reason"
    STATE_CONFIRMING = "confirming"
    STATE_COMPLETE = "complete"
    STATE_CANCELLED = "cancelled"
    
    def __init__(self):
        """Initialize Booking Conversation Agent"""
        self.booking_agent = BookingAgent()
        self.intent_classifier = IntentClassifier()
        self.calendar_service = CalendarService()
    
    def initialize_booking(self, student_id: str, student_program: Optional[str] = None) -> Dict:
        """
        Initialize a new booking conversation
        
        Args:
            student_id: Student ASU ID
            student_program: Optional program level from student profile
            
        Returns:
            Dictionary with initial state and message
        """
        booking_context = {
            "student_id": student_id,
            "program_level": None,  # Always start fresh, ask for program level
            "advisor_id": None,
            "advisor_name": None,
            "slot_datetime": None,
            "preferred_date": None,
            "preferred_time": None,
            "reason": None,
            "state": self.STATE_NEED_PROGRAM,  # Always start with program level selection
            "available_advisors": [],
            "available_slots": [],
            "suggested_slots": []
        }
        
        # Always ask for program level first (MS or BS)
        message = "I'd be happy to help you book an appointment! Are you an undergraduate (BS) or graduate (MS) student?"
        
        return {
            "success": True,
            "booking_context": booking_context,
            "message": message,
            "state": booking_context["state"]
        }
    
    def process_user_message(self, user_input: str, booking_context: Dict) -> Dict:
        """
        Process user message in booking conversation
        
        Args:
            user_input: User's message
            booking_context: Current booking context/state
            
        Returns:
            Dictionary with updated context, response message, and next action
        """
        user_input_lower = user_input.lower().strip()
        
        # Check for cancellation
        if any(word in user_input_lower for word in ["cancel", "nevermind", "forget it", "stop"]):
            return {
                "success": True,
                "booking_context": {**booking_context, "state": self.STATE_CANCELLED},
                "message": "Booking cancelled. Let me know if you'd like to start over!",
                "state": self.STATE_CANCELLED,
                "action": "cancel"
            }
        
        # Check for confirmation
        if booking_context["state"] == self.STATE_CONFIRMING:
            if any(word in user_input_lower for word in ["yes", "confirm", "book it", "sure", "okay", "ok"]):
                return self._finalize_booking(booking_context)
            elif any(word in user_input_lower for word in ["no", "change", "modify", "edit"]):
                booking_context["state"] = self.STATE_NEED_DATE
                return {
                    "success": True,
                    "booking_context": booking_context,
                    "message": "No problem! What would you like to change? (date, time, or advisor)",
                    "state": booking_context["state"],
                    "action": "modify"
                }
        
        # Process based on current state
        current_state = booking_context.get("state", self.STATE_NEED_PROGRAM)
        
        if current_state == self.STATE_NEED_PROGRAM:
            return self._handle_program_selection(user_input, booking_context)
        elif current_state == self.STATE_NEED_ADVISOR:
            return self._handle_advisor_selection(user_input, booking_context)
        elif current_state == self.STATE_NEED_DATE:
            return self._handle_date_selection(user_input, booking_context)
        elif current_state == self.STATE_NEED_TIME:
            return self._handle_time_selection(user_input, booking_context)
        elif current_state == self.STATE_NEED_REASON:
            return self._handle_reason_input(user_input, booking_context)
        else:
            return {
                "success": False,
                "booking_context": booking_context,
                "message": "I'm not sure what to do. Let's start over!",
                "state": current_state,
                "action": "error"
            }
    
    def _handle_program_selection(self, user_input: str, booking_context: Dict) -> Dict:
        """Handle program level selection"""
        user_lower = user_input.lower().strip()
        
        # Check for undergraduate/BS
        if any(term in user_lower for term in ["undergraduate", "undergrad", "bachelor", "bs", "b.s"]):
            program = "undergraduate"
        # Check for graduate/MS
        elif any(term in user_lower for term in ["graduate", "master", "grad", "ms", "m.s", "masters"]):
            program = "graduate"
        else:
            return {
                "success": False,
                "booking_context": booking_context,
                "message": "I didn't catch that. Are you an undergraduate (BS) or graduate (MS) student?",
                "state": self.STATE_NEED_PROGRAM,
                "action": "clarify"
            }
        
        booking_context["program_level"] = program
        advisors = self._get_advisors_for_program(program)
        booking_context["available_advisors"] = advisors
        booking_context["state"] = self.STATE_NEED_ADVISOR
        
        return {
            "success": True,
            "booking_context": booking_context,
            "message": "Please select an advisor from the options below:",
            "state": self.STATE_NEED_ADVISOR,
            "action": "show_advisors"
        }
    
    def _handle_advisor_selection(self, user_input: str, booking_context: Dict) -> Dict:
        """Handle advisor selection"""
        advisors = booking_context.get("available_advisors", [])
        
        # Try to match advisor by name
        user_lower = user_input.lower()
        selected_advisor = None
        
        for advisor in advisors:
            advisor_name_lower = advisor["name"].lower()
            advisor_email_lower = advisor["email"].lower()
            
            # Check if user input matches advisor name or email
            if (advisor_name_lower in user_lower or 
                user_lower in advisor_name_lower or
                advisor_email_lower in user_lower or
                any(word in advisor_name_lower for word in user_lower.split() if len(word) > 3)):
                selected_advisor = advisor
                break
        
        # Check for advisor ID if user clicked a button
        if not selected_advisor:
            # Try to extract advisor_id from input (if it's a click)
            for advisor in advisors:
                if advisor["advisor_id"] in user_input:
                    selected_advisor = advisor
                    break
        
        if not selected_advisor:
            return {
                "success": False,
                "booking_context": booking_context,
                "message": "I couldn't find that advisor. Please select one from the options below:",
                "state": self.STATE_NEED_ADVISOR,
                "action": "clarify"
            }
        
        booking_context["advisor_id"] = selected_advisor["advisor_id"]
        booking_context["advisor_name"] = selected_advisor["name"]
        booking_context["state"] = self.STATE_NEED_DATE
        
        return {
            "success": True,
            "booking_context": booking_context,
            "message": f"Great! I've selected **{selected_advisor['name']}** ({selected_advisor['title']}).\n\n" +
                       "What date would you like to schedule your appointment? You can say something like 'next Monday', 'March 15th', or 'next week'.",
            "state": self.STATE_NEED_DATE,
            "action": "advisor_selected"
        }
    
    def _handle_date_selection(self, user_input: str, booking_context: Dict) -> Dict:
        """Handle date selection - uses LLM first, then falls back to rule-based parsing"""
        advisor_id = booking_context.get("advisor_id")
        if not advisor_id:
            return {
                "success": False,
                "booking_context": booking_context,
                "message": "Please select an advisor first.",
                "state": self.STATE_NEED_ADVISOR,
                "action": "error"
            }
        
        parsed_dates = []
        
        # Step 1: Try LLM-based extraction first
        try:
            extracted_info = self.intent_classifier.extract_booking_info(user_input)
            llm_date = extracted_info.get("preferred_date")
            
            if llm_date and llm_date.lower() != "null":
                # LLM extracted a date - try to parse it
                # LLM might return formats like "next Monday", "2025-11-20", "November 20, 2025"
                llm_parsed = self._parse_date_from_text(llm_date)
                if llm_parsed:
                    if llm_parsed >= date.today():
                        max_date = date.today() + timedelta(days=30)
                        if llm_parsed <= max_date:
                            parsed_dates.append(llm_parsed)
        except Exception as e:
            print(f"LLM date extraction failed: {e}, falling back to rule-based parsing")
        
        # Step 2: If LLM didn't work, use rule-based parsing
        if not parsed_dates:
            user_lower = user_input.lower()
            
            # Check for multiple dates separated by "or", "and", ","
            date_separators = [" or ", " and ", ", ", ","]
            date_parts = [user_input]
            for sep in date_separators:
                if sep in user_lower:
                    date_parts = user_input.split(sep)
                    break
            
            for part in date_parts:
                parsed_date = self._parse_date_from_text(part.strip())
                if parsed_date:
                    # Validate date
                    if parsed_date >= date.today():
                        max_date = date.today() + timedelta(days=30)
                        if parsed_date <= max_date:
                            parsed_dates.append(parsed_date)
            
            # If no dates found, try parsing the whole input as a single date
            if not parsed_dates:
                parsed_date = self._parse_date_from_text(user_input)
                if parsed_date:
                    if parsed_date >= date.today():
                        max_date = date.today() + timedelta(days=30)
                        if parsed_date <= max_date:
                            parsed_dates = [parsed_date]
        
        if not parsed_dates:
            return {
                "success": False,
                "booking_context": booking_context,
                "message": "I couldn't understand that date. Please try again, like 'next Monday', 'March 15th', or 'next week'.",
                "state": self.STATE_NEED_DATE,
                "action": "clarify"
            }
        
        # Remove duplicates and sort dates
        parsed_dates = sorted(list(set(parsed_dates)))
        
        # Get available slots for all parsed dates
        start_date = min(parsed_dates)
        end_date = max(parsed_dates)
        
        available_slots = self.booking_agent.get_available_slots(
            advisor_id, start_date, end_date
        )
        
        # Filter to only slots on the selected dates
        date_slots = [slot for slot in available_slots if slot.date() in parsed_dates]
        
        if not date_slots:
            # No slots on any of the requested dates
            if len(parsed_dates) == 1:
                # Single date - suggest alternatives
                parsed_date = parsed_dates[0]
                booking_context["preferred_date"] = parsed_date
                
                # Look for alternatives in the next 2 weeks
                start_search = parsed_date + timedelta(days=1)
                end_search = parsed_date + timedelta(days=14)
                alt_slots = self.booking_agent.get_available_slots(
                    advisor_id, start_search, end_search
                )
                
                if alt_slots:
                    from collections import defaultdict
                    slots_by_date = defaultdict(list)
                    for slot in alt_slots:
                        slots_by_date[slot.date()].append(slot)
                    
                    sorted_dates = sorted(slots_by_date.items(), key=lambda x: len(x[1]), reverse=True)
                    top_dates = sorted_dates[:5]
                    suggested_dates = [d[0] for d in top_dates]
                    all_suggested_slots = [slot for _, slots in top_dates for slot in slots[:3]]
                    
                    booking_context["suggested_slots"] = all_suggested_slots
                    booking_context["suggested_dates"] = suggested_dates
                    
                    date_options = []
                    for d, slots in top_dates:
                        slot_count = len(slots)
                        date_str = d.strftime("%A, %B %d")
                        date_options.append(f"• {date_str} ({slot_count} available slot{'s' if slot_count > 1 else ''})")
                    
                    dates_list = "\n".join(date_options[:5])
                    
                    return {
                        "success": False,
                        "booking_context": booking_context,
                        "message": f"❌ Unfortunately, there are no available slots on {parsed_date.strftime('%A, %B %d, %Y')}.\n\n"
                                   f"Here are some alternative dates with available slots:\n\n"
                                   f"{dates_list}\n\n"
                                   f"Which date would you prefer?",
                        "state": self.STATE_NEED_DATE,
                        "action": "suggest_alternatives"
                    }
                else:
                    # Check further out (up to 30 days)
                    further_start = parsed_date + timedelta(days=15)
                    further_end = min(parsed_date + timedelta(days=30), date.today() + timedelta(days=30))
                    further_slots = self.booking_agent.get_available_slots(
                        advisor_id, further_start, further_end
                    )
                    
                    if further_slots:
                        from collections import defaultdict
                        slots_by_date = defaultdict(list)
                        for slot in further_slots:
                            slots_by_date[slot.date()].append(slot)
                        
                        sorted_dates = sorted(slots_by_date.items(), key=lambda x: len(x[1]), reverse=True)
                        top_dates = sorted_dates[:3]
                        suggested_dates = [d[0] for d in top_dates]
                        
                        booking_context["suggested_dates"] = suggested_dates
                        
                        date_options = []
                        for d, slots in top_dates:
                            date_str = d.strftime("%A, %B %d")
                            date_options.append(f"• {date_str} ({len(slots)} slot{'s' if len(slots) > 1 else ''})")
                        
                        dates_list = "\n".join(date_options)
                        
                        return {
                            "success": False,
                            "booking_context": booking_context,
                            "message": f"❌ No available slots on {parsed_date.strftime('%A, %B %d, %Y')} or in the next 2 weeks.\n\n"
                                       f"The next available dates are:\n\n"
                                       f"{dates_list}\n\n"
                                       f"Would you like to book one of these dates instead?",
                            "state": self.STATE_NEED_DATE,
                            "action": "suggest_alternatives"
                        }
                    else:
                        return {
                            "success": False,
                            "booking_context": booking_context,
                            "message": f"❌ Unfortunately, there are no available slots on {parsed_date.strftime('%A, %B %d, %Y')} "
                                       f"or in the next 30 days for this advisor.\n\n"
                                       f"Would you like to:\n"
                                       f"• Try a different advisor\n"
                                       f"• Contact the advising office directly at 480-727-1874\n"
                                       f"• Try booking again later",
                            "state": self.STATE_NEED_DATE,
                            "action": "no_slots"
                        }
            else:
                # Multiple dates - suggest checking a wider range
                dates_str = ", ".join([d.strftime("%B %d") for d in parsed_dates])
                return {
                    "success": False,
                    "booking_context": booking_context,
                    "message": f"❌ Unfortunately, there are no available slots on {dates_str}.\n\n"
                               f"Would you like to try other dates?",
                    "state": self.STATE_NEED_DATE,
                    "action": "clarify"
                }
        
        booking_context["available_slots"] = date_slots
        booking_context["preferred_date"] = parsed_dates[0] if len(parsed_dates) == 1 else None
        booking_context["state"] = self.STATE_NEED_TIME
        
        # Create message based on number of dates
        if len(parsed_dates) == 1:
            date_msg = f"Perfect! Here are the available times on {parsed_dates[0].strftime('%A, %B %d, %Y')}. Please select a time slot below:"
        else:
            dates_str = " and ".join([d.strftime("%B %d") for d in parsed_dates])
            date_msg = f"Perfect! Here are the available times on {dates_str}. Please select a time slot below:"
        
        return {
            "success": True,
            "booking_context": booking_context,
            "message": date_msg,
            "state": self.STATE_NEED_TIME,
            "action": "show_slots"
        }
    
    def _handle_time_selection(self, user_input: str, booking_context: Dict) -> Dict:
        """Handle time selection - uses LLM first, then falls back to rule-based parsing"""
        available_slots = booking_context.get("available_slots", [])
        
        if not available_slots:
            return {
                "success": False,
                "booking_context": booking_context,
                "message": "Please select a date first.",
                "state": self.STATE_NEED_DATE,
                "action": "error"
            }
        
        selected_slot = None
        
        # Step 1: Try LLM-based extraction first
        try:
            extracted_info = self.intent_classifier.extract_booking_info(user_input)
            llm_time = extracted_info.get("preferred_time")
            
            if llm_time and llm_time.lower() != "null":
                # LLM extracted a time - try to match it to available slots
                # LLM might return formats like "2 PM", "14:00", "afternoon", "morning"
                selected_slot = self._match_time_from_input(llm_time, available_slots)
                
                # If direct match fails, try parsing the LLM time string
                if not selected_slot:
                    selected_slot = self._match_time_from_input(user_input, available_slots)
        except Exception as e:
            print(f"LLM time extraction failed: {e}, falling back to rule-based parsing")
        
        # Step 2: If LLM didn't work, use rule-based parsing
        if not selected_slot:
            selected_slot = self._match_time_from_input(user_input, available_slots)
        
        if not selected_slot:
            return {
                "success": False,
                "booking_context": booking_context,
                "message": "I couldn't match that time. Please select one of the available time slots below:",
                "state": self.STATE_NEED_TIME,
                "action": "clarify"
            }
        
        booking_context["slot_datetime"] = selected_slot
        booking_context["state"] = self.STATE_NEED_REASON
        
        formatted_time = self.calendar_service.format_slot_display(selected_slot)
        
        return {
            "success": True,
            "booking_context": booking_context,
            "message": f"Excellent! I've selected {formatted_time}.\n\n" +
                       "Is there a specific reason for this appointment? (e.g., course planning, graduation requirements, etc.) " +
                       "This is optional - you can say 'skip' or 'none'.",
            "state": self.STATE_NEED_REASON,
            "action": "time_selected"
        }
    
    def _handle_reason_input(self, user_input: str, booking_context: Dict) -> Dict:
        """Handle reason input (optional)"""
        user_lower = user_input.lower().strip()
        
        if user_lower in ["skip", "none", "no reason", "n/a", ""]:
            booking_context["reason"] = None
        else:
            booking_context["reason"] = user_input.strip()
        
        booking_context["state"] = self.STATE_CONFIRMING
        
        # Generate confirmation message
        advisor_name = booking_context.get("advisor_name", "the advisor")
        slot = booking_context.get("slot_datetime")
        reason = booking_context.get("reason")
        
        formatted_date = slot.strftime("%A, %B %d, %Y")
        formatted_time = self.calendar_service.format_slot_time_only(slot)
        
        confirmation_msg = f"**Appointment Summary:**\n\n"
        confirmation_msg += f"• **Advisor:** {advisor_name}\n"
        confirmation_msg += f"• **Date:** {formatted_date}\n"
        confirmation_msg += f"• **Time:** {formatted_time}\n"
        if reason:
            confirmation_msg += f"• **Reason:** {reason}\n"
        confirmation_msg += f"\nDoes this look correct? Say 'yes' to confirm or 'no' to make changes."
        
        return {
            "success": True,
            "booking_context": booking_context,
            "message": confirmation_msg,
            "state": self.STATE_CONFIRMING,
            "action": "confirm"
        }
    
    def _finalize_booking(self, booking_context: Dict) -> Dict:
        """Finalize the booking"""
        student_id = booking_context.get("student_id")
        advisor_id = booking_context.get("advisor_id")
        slot_datetime = booking_context.get("slot_datetime")
        reason = booking_context.get("reason")
        
        if not all([student_id, advisor_id, slot_datetime]):
            return {
                "success": False,
                "booking_context": booking_context,
                "message": "Missing required information. Let's start over.",
                "state": self.STATE_NEED_PROGRAM,
                "action": "error"
            }
        
        # Book the appointment
        result = self.booking_agent.book_appointment(
            student_id=student_id,
            advisor_id=advisor_id,
            slot_datetime=slot_datetime,
            reason=reason
        )
        
        if not result["success"]:
            return {
                "success": False,
                "booking_context": booking_context,
                "message": f"Sorry, I couldn't book the appointment: {result['message']}. Let's try again.",
                "state": self.STATE_NEED_DATE,
                "action": "error"
            }
        
        # Try to send confirmation email
        email_sent = False
        try:
            from services.EmailService import EmailService
            email_service = EmailService()
            if email_service.is_configured:
                email_result = email_service.send_appointment_confirmation(result["appointment"])
                email_sent = email_result["success"]
        except Exception:
            pass
        
        appointment = result["appointment"]
        formatted_date = slot_datetime.strftime("%A, %B %d, %Y")
        formatted_time = self.calendar_service.format_slot_time_only(slot_datetime)
        
        success_msg = f"✅ **Appointment booked successfully!**\n\n"
        success_msg += f"**Appointment ID:** {appointment.appointment_id}\n"
        success_msg += f"**Date:** {formatted_date}\n"
        success_msg += f"**Time:** {formatted_time}\n"
        success_msg += f"**Status:** {appointment.status.title()}\n"
        
        if email_sent:
            success_msg += "\n📧 A confirmation email has been sent to your email address."
        
        booking_context["state"] = self.STATE_COMPLETE
        
        return {
            "success": True,
            "booking_context": booking_context,
            "message": success_msg,
            "state": self.STATE_COMPLETE,
            "action": "booked",
            "appointment": appointment
        }
    
    def _get_advisors_for_program(self, program_level: str) -> List[Dict]:
        """Get advisors for a program level"""
        from database.Database import get_session
        from database.models import Advisor
        
        db = get_session()
        try:
            advisors = db.query(Advisor).filter(
                Advisor.program_level == program_level.lower()
            ).all()
            
            advisor_list = []
            for advisor in advisors:
                advisor_list.append({
                    "advisor_id": advisor.advisor_id,
                    "name": advisor.name,
                    "email": advisor.email,
                    "title": advisor.title,
                    "phone": advisor.phone,
                    "office_location": advisor.office_location
                })
            
            return advisor_list
            
        except Exception as e:
            print(f"Error getting advisors: {e}")
            return []
        finally:
            db.close()
    
    def _generate_advisor_selection_message(self, advisors: List[Dict]) -> str:
        """Generate message showing available advisors"""
        if not advisors:
            return "No advisors available for this program level."
        
        msg = "Here are the available advisors:\n\n"
        for i, advisor in enumerate(advisors, 1):
            msg += f"**{i}. {advisor['name']}** - {advisor['title']}\n"
            msg += f"   📧 {advisor['email']} | 📞 {advisor.get('phone', 'N/A')}\n"
            if advisor.get('office_location'):
                msg += f"   📍 {advisor['office_location']}\n"
            msg += "\n"
        
        msg += "Which advisor would you like to meet with? You can say their name or number."
        return msg
    
    def _parse_date_from_text(self, text: str) -> Optional[date]:
        """Parse date from natural language text"""
        text_lower = text.lower().strip()
        today = date.today()
        
        # Handle relative dates
        # Check for "today" and "tomorrow" first
        if "today" in text_lower:
            return today
        elif "tomorrow" in text_lower:
            return today + timedelta(days=1)
        
        # Check for "next week [day]" patterns first (before generic "next week")
        # This ensures "next week Monday" is parsed correctly
        if "next week monday" in text_lower or ("next week" in text_lower and "monday" in text_lower):
            # Get Monday of next week (7 days from this Monday)
            days_until_this_monday = (0 - today.weekday()) % 7  # Monday is 0
            if days_until_this_monday == 0:
                days_until_this_monday = 7  # If today is Monday, get next Monday
            return today + timedelta(days=days_until_this_monday + 7)  # Next week's Monday
        elif "next week tuesday" in text_lower or ("next week" in text_lower and "tuesday" in text_lower):
            days_until_this_tuesday = (1 - today.weekday()) % 7
            if days_until_this_tuesday == 0:
                days_until_this_tuesday = 7
            return today + timedelta(days=days_until_this_tuesday + 7)
        elif "next week wednesday" in text_lower or ("next week" in text_lower and "wednesday" in text_lower):
            days_until_this_wednesday = (2 - today.weekday()) % 7
            if days_until_this_wednesday == 0:
                days_until_this_wednesday = 7
            return today + timedelta(days=days_until_this_wednesday + 7)
        elif "next week thursday" in text_lower or ("next week" in text_lower and "thursday" in text_lower):
            days_until_this_thursday = (3 - today.weekday()) % 7
            if days_until_this_thursday == 0:
                days_until_this_thursday = 7
            return today + timedelta(days=days_until_this_thursday + 7)
        elif "next week friday" in text_lower or ("next week" in text_lower and "friday" in text_lower):
            days_until_this_friday = (4 - today.weekday()) % 7
            if days_until_this_friday == 0:
                days_until_this_friday = 7
            return today + timedelta(days=days_until_this_friday + 7)
        
        # Check for "next [day]" patterns (this week or next week)
        elif "next monday" in text_lower:
            days_ahead = 0 - today.weekday()  # Monday is 0
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        elif "next tuesday" in text_lower:
            days_ahead = 1 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        elif "next wednesday" in text_lower:
            days_ahead = 2 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        elif "next thursday" in text_lower:
            days_ahead = 3 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        elif "next friday" in text_lower:
            days_ahead = 4 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        
        # Check for just day names (without "next")
        elif "monday" in text_lower and "next" not in text_lower:
            days_ahead = 0 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        elif "tuesday" in text_lower and "next" not in text_lower:
            days_ahead = 1 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        elif "wednesday" in text_lower and "next" not in text_lower:
            days_ahead = 2 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        elif "thursday" in text_lower and "next" not in text_lower:
            days_ahead = 3 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        elif "friday" in text_lower and "next" not in text_lower:
            days_ahead = 4 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        
        # Generic "next week" - default to Monday of next week
        elif "next week" in text_lower:
            # Return Monday of next week (start of the week)
            days_until_monday = (0 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7  # If today is Monday, get next Monday
            return today + timedelta(days=days_until_monday + 7)
        
        # Try to parse with dateutil
        try:
            parsed = date_parser.parse(text, fuzzy=True, default=datetime.now())
            return parsed.date()
        except (ValueError, TypeError):
            pass
        
        # Try to extract date patterns
        # Look for patterns like "March 15", "3/15", "15th of March"
        month_patterns = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        }
        
        for month_name, month_num in month_patterns.items():
            if month_name in text_lower:
                # Try to extract day
                day_match = re.search(r'\b(\d{1,2})\b', text)
                if day_match:
                    try:
                        day = int(day_match.group(1))
                        year = today.year
                        # If the date is in the past, assume next year
                        test_date = date(year, month_num, day)
                        if test_date < today:
                            year += 1
                        return date(year, month_num, day)
                    except ValueError:
                        pass
        
        return None
    
    def _match_time_from_input(self, user_input: str, available_slots: List[datetime]) -> Optional[datetime]:
        """Match time from user input to available slots - handles various time formats"""
        user_lower = user_input.lower().strip()
        
        # Check if user clicked a slot (contains ISO format)
        for slot in available_slots:
            if slot.isoformat() in user_input:
                return slot
        
        # Handle time period preferences (morning, afternoon, evening)
        time_preference = None
        if "morning" in user_lower:
            time_preference = (8, 12)  # 8 AM to 12 PM
        elif "afternoon" in user_lower:
            time_preference = (12, 17)  # 12 PM to 5 PM
        elif "evening" in user_lower:
            time_preference = (17, 20)  # 5 PM to 8 PM
        
        # If time preference is specified, filter slots first
        filtered_slots = available_slots
        if time_preference:
            filtered_slots = [
                slot for slot in available_slots
                if time_preference[0] <= slot.hour < time_preference[1]
            ]
            # If no slots match preference, use all slots
            if not filtered_slots:
                filtered_slots = available_slots
        
        # Try to parse time from text
        time_patterns = [
            r'(\d{1,2})\s*(am|pm)',
            r'(\d{1,2}):(\d{2})\s*(am|pm)',
            r'(\d{1,2})\s*o\'?clock',
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, user_lower)
            if match:
                try:
                    hour = int(match.group(1))
                    minute = int(match.group(2)) if len(match.groups()) > 2 and match.group(2).isdigit() else 0
                    period = match.group(-1) if match.groups() > 0 else ""
                    
                    # Convert to 24-hour format
                    if "pm" in period and hour != 12:
                        hour += 12
                    elif "am" in period and hour == 12:
                        hour = 0
                    
                    # Find closest matching slot
                    target_time = time(hour, minute)
                    best_match = None
                    min_diff = float('inf')
                    
                    for slot in filtered_slots:
                        slot_time = slot.time()
                        diff = abs((slot_time.hour * 60 + slot_time.minute) - (target_time.hour * 60 + target_time.minute))
                        if diff < min_diff:
                            min_diff = diff
                            best_match = slot
                    
                    if best_match and min_diff <= 30:  # Within 30 minutes
                        return best_match
                except (ValueError, IndexError):
                    continue
        
        # If time preference was specified but no exact match, return first slot in that period
        if time_preference and filtered_slots:
            return filtered_slots[0]
        
        # Try to match by number (e.g., "first one", "option 1")
        num_match = re.search(r'\b(\d+)\b', user_input)
        if num_match:
            try:
                index = int(num_match.group(1)) - 1
                if 0 <= index < len(filtered_slots):
                    return filtered_slots[index]
            except (ValueError, IndexError):
                pass
        
        return None

