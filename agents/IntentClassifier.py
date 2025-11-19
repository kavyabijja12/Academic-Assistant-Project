"""
Intent Classifier
Uses LangChain to classify user intent: "booking" vs "question"
"""

import sys
from pathlib import Path
import os
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()


class IntentClassifier:
    """Classifies user intent using LangChain/Gemini"""
    
    def __init__(self):
        """Initialize Intent Classifier"""
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel("models/gemini-2.5-flash")
    
    def detect_intent(self, user_input: str) -> Dict:
        """
        Detect user intent from input
        
        Args:
            user_input: User's message/query
            
        Returns:
            Dictionary with:
            - intent: "booking" or "question"
            - confidence: "high", "medium", or "low"
            - reasoning: str (explanation)
        """
        if not user_input or not user_input.strip():
            return {
                "intent": "question",
                "confidence": "low",
                "reasoning": "Empty input"
            }
        
        # Keywords that strongly indicate booking intent
        booking_keywords = [
            "book", "schedule", "appointment", "meeting", "advising",
            "meet with", "see advisor", "talk to advisor", "set up",
            "make appointment", "reserve", "slot", "time slot"
        ]
        
        # Keywords that strongly indicate question intent
        question_keywords = [
            "what", "how", "when", "where", "why", "which", "who",
            "tell me", "explain", "information", "details", "requirements",
            "courses", "program", "degree", "graduation"
        ]
        
        user_lower = user_input.lower()
        
        # Count keyword matches
        booking_matches = sum(1 for keyword in booking_keywords if keyword in user_lower)
        question_matches = sum(1 for keyword in question_keywords if keyword in user_lower)
        
        # If strong keyword match, use that (fast path)
        if booking_matches > 0 and booking_matches > question_matches:
            return {
                "intent": "booking",
                "confidence": "high",
                "reasoning": f"Detected booking keywords: {booking_matches} matches"
            }
        elif question_matches > 0 and question_matches > booking_matches:
            return {
                "intent": "question",
                "confidence": "high",
                "reasoning": f"Detected question keywords: {question_matches} matches"
            }
        
        # If ambiguous, use LLM to classify
        return self._classify_with_llm(user_input)
    
    def _classify_with_llm(self, user_input: str) -> Dict:
        """
        Use LLM to classify intent when keywords are ambiguous
        
        Args:
            user_input: User's message
            
        Returns:
            Dictionary with intent classification
        """
        prompt = f"""You are an intent classifier for an ASU academic assistant system.

Classify the following user input into one of two categories:
1. "booking" - User wants to book/schedule an appointment with an advisor
2. "question" - User is asking a question about the program, courses, requirements, etc.

User input: "{user_input}"

Respond with ONLY one word: "booking" or "question"
Then on a new line, provide a brief reason (one sentence).

Example response:
booking
User wants to schedule an appointment with an advisor
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = response.text.strip()
            
            # Parse response
            lines = result.split('\n')
            intent_line = lines[0].strip().lower()
            reasoning = lines[1].strip() if len(lines) > 1 else "LLM classification"
            
            # Extract intent
            if "booking" in intent_line:
                intent = "booking"
                confidence = "medium"  # LLM classification is medium confidence
            elif "question" in intent_line:
                intent = "question"
                confidence = "medium"
            else:
                # Default to question if unclear
                intent = "question"
                confidence = "low"
                reasoning = "Unclear intent, defaulting to question"
            
            return {
                "intent": intent,
                "confidence": confidence,
                "reasoning": reasoning
            }
            
        except Exception as e:
            # Fallback: default to question
            return {
                "intent": "question",
                "confidence": "low",
                "reasoning": f"LLM classification failed: {str(e)}, defaulting to question"
            }
    
    def extract_booking_info(self, user_input: str) -> Dict:
        """
        Extract booking-related information from user input (optional, for future use)
        
        Args:
            user_input: User's message
            
        Returns:
            Dictionary with extracted info (advisor name, date, time, etc.)
        """
        # This is a placeholder for future natural language parsing
        # For now, we use structured UI, but this could be enhanced later
        
        prompt = f"""Extract booking information from this user input:

User input: "{user_input}"

Extract:
- advisor_name: Name of advisor (if mentioned)
- preferred_date: Date preference (if mentioned)
- preferred_time: Time preference (if mentioned)
- reason: Reason for appointment (if mentioned)

Respond in JSON format:
{{
    "advisor_name": "name or null",
    "preferred_date": "date or null",
    "preferred_time": "time or null",
    "reason": "reason or null"
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            # Parse JSON response (simplified - in production, use proper JSON parsing)
            # For now, return empty dict
            return {
                "advisor_name": None,
                "preferred_date": None,
                "preferred_time": None,
                "reason": None
            }
        except Exception as e:
            return {
                "advisor_name": None,
                "preferred_date": None,
                "preferred_time": None,
                "reason": None
            }


