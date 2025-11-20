"""
Agent Controller
Routes requests between booking flow and RAG system based on user intent
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.IntentClassifier import IntentClassifier
from agents.BookingAgent import BookingAgent
from agents.AuthenticationAgent import AuthenticationAgent
from agents.BookingConversationAgent import BookingConversationAgent


class AgentController:
    """Routes requests to appropriate agents based on intent"""
    
    def __init__(self):
        """Initialize Agent Controller"""
        self.intent_classifier = IntentClassifier()
        self.booking_agent = BookingAgent()
        self.auth_agent = AuthenticationAgent()
        self.booking_conversation_agent = BookingConversationAgent()
    
    def route_request(self, user_input: str, student_context: Optional[Dict] = None) -> Dict:
        """
        Route user request to appropriate handler
        
        Args:
            user_input: User's message/query
            student_context: Optional dict with student info (asu_id, authenticated, etc.)
            
        Returns:
            Dictionary with:
            - intent: "booking" or "question"
            - action: "start_booking" or "ask_question"
            - message: str (for UI)
            - data: dict (additional data if needed)
        """
        # Detect intent
        intent_result = self.intent_classifier.detect_intent(user_input)
        intent = intent_result["intent"]
        
        if intent == "booking":
            # Check if student is authenticated
            if not student_context or not student_context.get("authenticated"):
                return {
                    "intent": "booking",
                    "action": "require_authentication",
                    "message": "Please authenticate to book an appointment",
                    "data": {
                        "requires_auth": True,
                        "intent_confidence": intent_result["confidence"]
                    }
                }
            
            # Student is authenticated, start conversational booking flow
            return {
                "intent": "booking",
                "action": "start_booking",
                "message": "Starting appointment booking process",
                "data": {
                    "student_id": student_context.get("asu_id"),
                    "program_level": student_context.get("program_level"),
                    "intent_confidence": intent_result["confidence"]
                }
            }
        else:
            # Question intent - route to RAG system
            return {
                "intent": "question",
                "action": "ask_question",
                "message": "Processing your question",
                "data": {
                    "query": user_input,
                    "intent_confidence": intent_result["confidence"]
                }
            }
    
    def handle_booking_request(self, student_id: str, user_input: str) -> Dict:
        """
        Handle booking request (after authentication)
        
        Args:
            student_id: Student ASU ID
            user_input: User's booking request
            
        Returns:
            Dictionary with booking flow information
        """
        # Get student info
        student = self.auth_agent.get_student_info(student_id)
        
        if not student:
            return {
                "success": False,
                "message": "Student not found"
            }
        
        return {
            "success": True,
            "student": {
                "asu_id": student.asu_id,
                "name": student.name,
                "email": student.email,
                "program_level": student.program_level
            },
            "message": "Ready to book appointment"
        }
    
    def get_available_advisors(self, program_level: str) -> list:
        """
        Get available advisors for a program level
        
        Args:
            program_level: "undergraduate" or "graduate"
            
        Returns:
            List of advisor dictionaries
        """
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
    
    def process_booking_flow(self, student_id: str, advisor_id: str, slot_datetime: datetime, reason: Optional[str] = None) -> Dict:
        """
        Process the complete booking flow
        
        Args:
            student_id: Student ASU ID
            advisor_id: Advisor email/ID
            slot_datetime: Selected appointment datetime
            reason: Optional reason for appointment
            
        Returns:
            Dictionary with booking result
        """
        # Book appointment
        booking_result = self.booking_agent.book_appointment(
            student_id=student_id,
            advisor_id=advisor_id,
            slot_datetime=slot_datetime,
            reason=reason
        )
        
        if not booking_result["success"]:
            return booking_result
        
        appointment = booking_result["appointment"]
        
        # Send confirmation email (if email service is configured)
        try:
            from services.EmailService import EmailService
            email_service = EmailService()
            if email_service.is_configured:
                email_result = email_service.send_appointment_confirmation(appointment)
                if email_result["success"]:
                    booking_result["email_sent"] = True
                else:
                    booking_result["email_sent"] = False
                    booking_result["email_error"] = email_result["message"]
            else:
                booking_result["email_sent"] = False
                booking_result["email_note"] = "Email service not configured"
        except Exception as e:
            booking_result["email_sent"] = False
            booking_result["email_error"] = str(e)
        
        return booking_result
    
    def initialize_booking_conversation(self, student_id: str, student_program: Optional[str] = None) -> Dict:
        """
        Initialize a conversational booking session
        
        Args:
            student_id: Student ASU ID
            student_program: Optional program level from student profile
            
        Returns:
            Dictionary with initial booking context and message
        """
        return self.booking_conversation_agent.initialize_booking(student_id, student_program)
    
    def process_booking_message(self, user_input: str, booking_context: Dict) -> Dict:
        """
        Process a user message in the booking conversation
        
        Args:
            user_input: User's message
            booking_context: Current booking context/state
            
        Returns:
            Dictionary with updated context, response message, and next action
        """
        return self.booking_conversation_agent.process_user_message(user_input, booking_context)

