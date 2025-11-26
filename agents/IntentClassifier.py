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
        Detect user intent from input with hierarchical categorization
        
        Args:
            user_input: User's message/query
            
        Returns:
            Dictionary with:
            - intent: "booking" or "question" (or hierarchical "question:subcategory")
            - category: Full hierarchical category (e.g., "question:program_requirements")
            - confidence: "high", "medium", or "low"
            - reasoning: str (explanation)
        """
        if not user_input or not user_input.strip():
            return {
                "intent": "question",
                "category": "question:course_information",
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
                "category": "booking",
                "confidence": "high",
                "reasoning": f"Detected booking keywords: {booking_matches} matches"
            }
        elif question_matches > 0 and question_matches > booking_matches:
            # Classify question subcategory
            question_type = self.classify_question_type(user_input)
            return {
                "intent": "question",
                "category": f"question:{question_type}",
                "confidence": "high",
                "reasoning": f"Detected question keywords: {question_matches} matches"
            }
        
        # If ambiguous, use LLM to classify
        return self._classify_with_llm(user_input)
    
    def classify_question_type(self, user_input: str) -> str:
        """
        Classify question into subcategories
        
        Args:
            user_input: User's question/message
            
        Returns:
            Question subcategory string:
            - course_information
            - application_process
            - program_requirements
            - professor_information
        """
        user_lower = user_input.lower()
        
        # STEP 1: Check for Professor Information FIRST (highest priority)
        # Any mention of professor/professors/instructor should go here
        if ("professor" in user_lower or "professors" in user_lower or 
            "instructor" in user_lower or "faculty advisor" in user_lower or
            "academic advisor" in user_lower or "my advisor" in user_lower or
            "who teaches" in user_lower or "who is teaching" in user_lower):
            return "professor_information"
        
        # STEP 2: Check for Application Process
        if any(kw in user_lower for kw in ["apply", "application", "admission", "enroll", "register", 
                                           "applied project", "how to apply"]):
            return "application_process"
        
        # STEP 3: Check for Program Requirements
        if any(kw in user_lower for kw in ["requirement", "credit", "gpa", "graduation", 
                                           "degree requirement", "program requirement", 
                                           "graduation requirement", "specializations in"]):
            return "program_requirements"
        
        # STEP 4: Check for Course Information (most general, check last)
        if any(kw in user_lower for kw in ["course", "class", "syllabus", "schedule", 
                                           "ift ", "cse ", "course description"]):
            return "course_information"
        
        # STEP 5: If no keyword match, use LLM for classification
        return self._classify_question_with_llm(user_input)
    
    def _classify_question_with_llm(self, user_input: str) -> str:
        """
        Use LLM to classify question type when keywords are ambiguous
        
        Args:
            user_input: User's question
            
        Returns:
            Question subcategory string
        """
        prompt = f"""You are a question classifier for an ASU Information Technology academic assistant system.

Classify the following user question into ONE of these categories:
1. course_information - Questions about specific courses, course descriptions, course schedules, course content, course materials, which courses to take, listing courses
2. application_process - Questions about applying, admission process, enrollment, registration, applied project application, how to apply
3. program_requirements - Questions about graduation requirements, credit requirements, GPA requirements, prerequisites, core courses, degree requirements, program specializations (what specializations exist)
4. professor_information - Questions about professors, instructors, faculty members, who teaches a course, professor contact information, advisor information, academic advisor, faculty advisor, who is my advisor, professor name, instructor name, what a professor specializes in, professors who specialize in X, details about a professor, information about professors

CRITICAL RULES:
- If the question mentions a professor's NAME (e.g., "professor Tatiana Walsh", "professor X"), classify as professor_information
- If the question asks "what does professor X specialize in" or "professors who specialize in X", classify as professor_information
- If the question asks "tell me about professor" or "details about professor", classify as professor_information
- If the question asks about program specializations (what specializations exist in the program), classify as program_requirements
- If the question asks about courses (listing courses, course details), classify as course_information

User question: "{user_input}"

Respond with ONLY the category name (e.g., "course_information" or "professor_information").
Do not include any other text or explanation.
"""
        
        try:
            response = self.model.generate_content(prompt)
            category = response.text.strip().lower()
            
            # Validate category
            valid_categories = [
                "course_information",
                "application_process",
                "program_requirements",
                "professor_information"
            ]
            
            # Check if response contains a valid category
            for valid_cat in valid_categories:
                if valid_cat in category:
                    return valid_cat
            
            # Default to course_information if unclear
            return "course_information"
            
        except Exception as e:
            # Default to course_information on error
            return "course_information"
    
    def _classify_with_llm(self, user_input: str) -> Dict:
        """
        Use LLM to classify intent when keywords are ambiguous
        
        Args:
            user_input: User's message
            
        Returns:
            Dictionary with intent classification (hierarchical format)
        """
        prompt = f"""You are an intent classifier for an ASU academic assistant system.

Classify the following user input:
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
                category = "booking"
                confidence = "medium"  # LLM classification is medium confidence
            elif "question" in intent_line:
                intent = "question"
                # Classify question subcategory
                question_type = self.classify_question_type(user_input)
                category = f"question:{question_type}"
                confidence = "medium"
            else:
                # Default to question if unclear
                intent = "question"
                category = "question:course_information"
                confidence = "low"
                reasoning = "Unclear intent, defaulting to question"
            
            return {
                "intent": intent,
                "category": category,
                "confidence": confidence,
                "reasoning": reasoning
            }
            
        except Exception as e:
            # Fallback: default to question
            return {
                "intent": "question",
                "category": "question:course_information",
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
    
    def extract_date_period_info(self, user_input: str) -> Dict:
        """
        Extract date period information from user input using LLM
        Determines if input is a specific date or a period expression
        
        Args:
            user_input: User's date input
            
        Returns:
            Dictionary with period information:
            - type: "specific_date" or "period"
            - period: "month" | "year" | "week" | null
            - time_reference: "next" | "this" | "following" | null
            - week_position: "first" | "last" | "second" | null
            - day_range: {"start": int, "end": int} | null
            - specific_date: "YYYY-MM-DD" | null
        """
        prompt = f"""Analyze this date expression and extract period information. Return ONLY valid JSON, no other text.

User input: "{user_input}"

Classify the input as either:
1. "specific_date" - A specific date like "March 15", "next Monday", "December 5th"
2. "period" - A period expression like "next month", "next year first week", "this month last week"

If it's a period, extract:
- period: "month" | "year" | "week" | null
- time_reference: "next" | "this" | "following" | null
- week_position: "first" | "second" | "third" | "fourth" | "last" | null (only if period mentions a week)
- day_range: {{"start": int, "end": int}} | null (e.g., "first 5 days" -> {{"start": 1, "end": 5}})

If it's a specific date, extract:
- specific_date: Try to convert to YYYY-MM-DD format if possible, otherwise null

Examples:
- "next month" -> {{"type": "period", "period": "month", "time_reference": "next", "week_position": null, "day_range": null, "specific_date": null}}
- "next year first week" -> {{"type": "period", "period": "year", "time_reference": "next", "week_position": "first", "day_range": null, "specific_date": null}}
- "next month second week" -> {{"type": "period", "period": "month", "time_reference": "next", "week_position": "second", "day_range": null, "specific_date": null}}
- "this month last week" -> {{"type": "period", "period": "month", "time_reference": "this", "week_position": "last", "day_range": null, "specific_date": null}}
- "next month third week" -> {{"type": "period", "period": "month", "time_reference": "next", "week_position": "third", "day_range": null, "specific_date": null}}
- "next month first 5 days" -> {{"type": "period", "period": "month", "time_reference": "next", "week_position": null, "day_range": {{"start": 1, "end": 5}}, "specific_date": null}}
- "March 15" -> {{"type": "specific_date", "period": null, "time_reference": null, "week_position": null, "day_range": null, "specific_date": "2025-03-15"}}
- "next Monday" -> {{"type": "specific_date", "period": null, "time_reference": null, "week_position": null, "day_range": null, "specific_date": null}}

Respond with ONLY valid JSON in this exact format:
{{
    "type": "specific_date" or "period",
    "period": "month" or "year" or "week" or null,
    "time_reference": "next" or "this" or "following" or null,
    "week_position": "first" or "last" or "second" or null,
    "day_range": {{"start": int, "end": int}} or null,
    "specific_date": "YYYY-MM-DD" or null
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
                if json_block:
                    json_str = json_block.group(1)
                else:
                    json_str = result_text
            
            # Parse JSON
            period_info = json.loads(json_str)
            
            # Validate and clean up
            return {
                "type": period_info.get("type", "specific_date"),
                "period": period_info.get("period") if period_info.get("period") and period_info.get("period").lower() != "null" else None,
                "time_reference": period_info.get("time_reference") if period_info.get("time_reference") and period_info.get("time_reference").lower() != "null" else None,
                "week_position": period_info.get("week_position") if period_info.get("week_position") and period_info.get("week_position").lower() != "null" else None,
                "day_range": period_info.get("day_range") if period_info.get("day_range") else None,
                "specific_date": period_info.get("specific_date") if period_info.get("specific_date") and period_info.get("specific_date").lower() != "null" else None
            }
            
        except (json.JSONDecodeError, KeyError, Exception) as e:
            # If parsing fails, default to specific_date and try rule-based parsing
            return {
                "type": "specific_date",
                "period": None,
                "time_reference": None,
                "week_position": None,
                "day_range": None,
                "specific_date": None
            }


