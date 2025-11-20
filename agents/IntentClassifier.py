"""
Intent Classifier
Uses LangChain to classify user intent: "booking" vs "question"
"""

import sys
from pathlib import Path
import os
import json
import re
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
        Extract booking-related information from user input using LLM
        
        Args:
            user_input: User's message
            
        Returns:
            Dictionary with extracted info (advisor name, date, time, reason)
        """
        prompt = f"""Extract booking information from this user input. Return ONLY valid JSON, no other text.

User input: "{user_input}"

Extract the following information if mentioned:
- advisor_name: Name of advisor (if mentioned, otherwise null)
- preferred_date: Date preference in YYYY-MM-DD format or relative terms like "next Monday" (if mentioned, otherwise null)
- preferred_time: Time preference like "2 PM" or "14:00" (if mentioned, otherwise null)
- reason: Reason for appointment (if mentioned, otherwise null)

Respond with ONLY valid JSON in this exact format:
{{
    "advisor_name": "name or null",
    "preferred_date": "date string or null",
    "preferred_time": "time string or null",
    "reason": "reason or null"
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Try to extract JSON from response (might have markdown code blocks)
            json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                # Try to find JSON between ```json and ```
                json_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
                if json_block:
                    json_str = json_block.group(1)
                else:
                    json_str = result_text
            
            # Parse JSON
            extracted_info = json.loads(json_str)
            
            # Validate and clean up the extracted info
            return {
                "advisor_name": extracted_info.get("advisor_name") if extracted_info.get("advisor_name") and extracted_info.get("advisor_name").lower() != "null" else None,
                "preferred_date": extracted_info.get("preferred_date") if extracted_info.get("preferred_date") and extracted_info.get("preferred_date").lower() != "null" else None,
                "preferred_time": extracted_info.get("preferred_time") if extracted_info.get("preferred_time") and extracted_info.get("preferred_time").lower() != "null" else None,
                "reason": extracted_info.get("reason") if extracted_info.get("reason") and extracted_info.get("reason").lower() != "null" else None
            }
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return empty dict
            return {
                "advisor_name": None,
                "preferred_date": None,
                "preferred_time": None,
                "reason": None
            }
        except Exception as e:
            # On any other error, return empty dict
            return {
                "advisor_name": None,
                "preferred_date": None,
                "preferred_time": None,
                "reason": None
            }


