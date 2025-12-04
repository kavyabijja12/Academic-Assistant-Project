# Booking Appointment System - Current Implementation & LangChain Agentic Approach

## 📋 Table of Contents
1. [Current Booking System Architecture](#current-booking-system-architecture)
2. [How Booking Works Step-by-Step](#how-booking-works-step-by-step)
3. [Building a Full LangChain Agentic Booking System](#building-a-full-langchain-agentic-booking-system)

---

## Current Booking System Architecture

### Components Overview

The current booking system uses a **state machine-based conversational flow** with the following components:

1. **`BookingAgent`** (`agents/BookingAgent.py`)
   - Core booking operations (book, cancel, confirm appointments)
   - Database interactions
   - Calendar slot management

2. **`BookingConversationAgent`** (`agents/BookingConversationAgent.py`)
   - Manages conversational flow through states
   - Handles natural language input parsing
   - State transitions and validation

3. **`CalendarService`** (`services/CalendarService.py`)
   - Generates available time slots
   - Checks slot availability
   - Manages advisor calendars

4. **`IntentClassifier`** (`agents/IntentClassifier.py`)
   - Uses Gemini LLM for intent detection
   - Extracts booking information from user input
   - Classifies date/period expressions

5. **`AgentController`** (`agents/AgentController.py`)
   - Routes requests between booking and RAG systems
   - Coordinates booking conversation flow

---

## How Booking Works Step-by-Step

### 1. **Initialization Phase**

```python
# User initiates booking
controller.initialize_booking_conversation(student_id, student_program)
```

**What happens:**
- Creates a `booking_context` dictionary with initial state
- Sets state to `STATE_NEED_PROGRAM`
- Asks user: "Are you an undergraduate (BS) or graduate (MS) student?"

**State Machine States:**
```
initial → need_program → need_advisor → need_date → need_time → need_reason → confirming → complete
```

### 2. **Program Selection** (`STATE_NEED_PROGRAM`)

**User Input Examples:**
- "undergraduate", "BS", "bachelor"
- "graduate", "MS", "master"

**Processing:**
- `_handle_program_selection()` matches keywords
- Filters advisors by program level
- Transitions to `STATE_NEED_ADVISOR`

### 3. **Advisor Selection** (`STATE_NEED_ADVISOR`)

**User Input Examples:**
- Advisor name: "Dr. Smith"
- Advisor email: "smith@asu.edu"

**Processing:**
- `_handle_advisor_selection()` matches advisor name/email
- Stores `advisor_id` and `advisor_name` in context
- Transitions to `STATE_NEED_DATE`

### 4. **Date Selection** (`STATE_NEED_DATE`)

This is the most complex step with two paths:

#### Path A: Specific Date
**User Input Examples:**
- "March 15th"
- "next Monday"
- "tomorrow"

**Processing:**
1. Rule-based parsing (`_parse_date_from_text()`) tries to extract date
2. If fails, uses LLM (`IntentClassifier.extract_booking_info()`)
3. Validates date (not past, within 30 days, weekday)
4. Gets available slots for that date
5. Transitions to `STATE_NEED_TIME`

#### Path B: Vague/Period Expression
**User Input Examples:**
- "next month"
- "next week"
- "sometime soon"

**Processing:**
1. LLM classifies as "period" (`extract_date_period_info()`)
2. LLM extracts search window (`extract_search_window()`)
3. Finds first 5 working days with available slots
4. Shows user options: "Here are the first 5 available working days..."
5. User selects a date → back to Path A

### 5. **Time Selection** (`STATE_NEED_TIME`)

**User Input Examples:**
- "2 PM"
- "morning"
- "afternoon"
- ISO datetime string (from UI button click)

**Processing:**
1. `_match_time_from_input()` matches user input to available slots
2. Handles time preferences (morning, afternoon, evening)
3. Finds closest matching slot
4. Stores `slot_datetime` in context
5. Transitions to `STATE_NEED_REASON`

### 6. **Reason Input** (`STATE_NEED_REASON`) - Optional

**User Input Examples:**
- "course planning"
- "graduation requirements"
- "skip" or "none"

**Processing:**
- Stores reason or sets to `None`
- Transitions to `STATE_CONFIRMING`

### 7. **Confirmation** (`STATE_CONFIRMING`)

**User Input:**
- "yes" → proceeds to booking
- "no" → allows modifications

**Processing:**
- Shows appointment summary
- Waits for user confirmation

### 8. **Finalization** (`_finalize_booking()`)

**What happens:**
1. Calls `BookingAgent.book_appointment()`:
   - Validates student and advisor exist
   - Checks slot availability
   - Prevents duplicate bookings
   - Creates `Appointment` record in database
   - Marks slot as unavailable in calendar
   - Commits transaction

2. Sends confirmation email (if configured)

3. Returns success message with appointment details

---

## Building a Full LangChain Agentic Booking System

### Why Use LangChain Agents?

**Current System Limitations:**
- Manual state management
- Fixed conversation flow
- Limited flexibility for complex scenarios
- Hard to handle edge cases

**LangChain Agent Benefits:**
- Autonomous decision-making
- Dynamic tool selection
- Better error recovery
- More natural conversations
- ReAct (Reasoning + Acting) pattern

---

### Architecture Design

```
┌─────────────────────────────────────────────────────────┐
│              LangChain Agent (ReAct Pattern)             │
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │   LLM Core  │ ←──→ │   Memory     │                │
│  │  (Gemini)   │      │  (Context)   │                │
│  └──────────────┘      └──────────────┘                │
│         │                      │                        │
│         └──────────┬───────────┘                        │
│                    │                                     │
│         ┌──────────▼──────────┐                        │
│         │   Tool Selection     │                        │
│         │   (Function Calling) │                        │
│         └──────────┬───────────┘                        │
└────────────────────┼────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                        │
    ┌────▼────┐            ┌─────▼─────┐
    │ Tools  │            │  Tools    │
    │        │            │           │
    ├────────┤            ├───────────┤
    │get_    │            │book_      │
    │available│            │appointment│
    │_slots   │            │           │
    ├────────┤            ├───────────┤
    │check_  │            │cancel_    │
    │slot_   │            │appointment│
    │availability│        │           │
    ├────────┤            ├───────────┤
    │get_    │            │get_       │
    │advisors│            │appointments│
    └────────┘            └───────────┘
```

---

### Implementation Steps

#### Step 1: Define Tools (Functions)

Create LangChain tools that wrap your existing booking operations:

```python
from langchain.tools import tool
from typing import Optional
from datetime import datetime, date

@tool
def get_available_advisors(program_level: str) -> str:
    """Get list of available advisors for a program level.
    
    Args:
        program_level: Either 'undergraduate' or 'graduate'
    
    Returns:
        JSON string with list of advisors including name, email, title
    """
    from agents.BookingAgent import BookingAgent
    from database.Database import get_session
    from database.models import Advisor
    
    db = get_session()
    try:
        advisors = db.query(Advisor).filter(
            Advisor.program_level == program_level.lower()
        ).all()
        
        advisor_list = [
            {
                "advisor_id": a.advisor_id,
                "name": a.name,
                "email": a.email,
                "title": a.title
            }
            for a in advisors
        ]
        return json.dumps(advisor_list)
    finally:
        db.close()

@tool
def get_available_slots(advisor_id: str, start_date: str, end_date: str) -> str:
    """Get available appointment slots for an advisor within a date range.
    
    Args:
        advisor_id: Advisor email or ID
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        JSON string with list of available datetime slots
    """
    from agents.BookingAgent import BookingAgent
    from datetime import datetime
    
    booking_agent = BookingAgent()
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    
    slots = booking_agent.get_available_slots(advisor_id, start, end)
    slot_strings = [s.isoformat() for s in slots]
    return json.dumps(slot_strings)

@tool
def check_slot_availability(advisor_id: str, slot_datetime: str) -> str:
    """Check if a specific time slot is available for booking.
    
    Args:
        advisor_id: Advisor email or ID
        slot_datetime: Datetime in ISO format (YYYY-MM-DDTHH:MM:SS)
    
    Returns:
        'available' or 'unavailable'
    """
    from services.CalendarService import CalendarService
    from datetime import datetime
    
    calendar_service = CalendarService()
    slot = datetime.fromisoformat(slot_datetime)
    is_available = calendar_service.check_slot_availability(advisor_id, slot)
    return "available" if is_available else "unavailable"

@tool
def book_appointment(student_id: str, advisor_id: str, slot_datetime: str, reason: Optional[str] = None) -> str:
    """Book an appointment for a student.
    
    Args:
        student_id: Student ASU ID
        advisor_id: Advisor email or ID
        slot_datetime: Datetime in ISO format (YYYY-MM-DDTHH:MM:SS)
        reason: Optional reason for appointment
    
    Returns:
        JSON string with booking result: {"success": bool, "message": str, "appointment_id": str}
    """
    from agents.BookingAgent import BookingAgent
    from datetime import datetime
    
    booking_agent = BookingAgent()
    slot = datetime.fromisoformat(slot_datetime)
    
    result = booking_agent.book_appointment(
        student_id=student_id,
        advisor_id=advisor_id,
        slot_datetime=slot,
        reason=reason
    )
    
    return json.dumps({
        "success": result["success"],
        "message": result["message"],
        "appointment_id": result["appointment"].appointment_id if result.get("appointment") else None
    })

@tool
def get_student_appointments(student_id: str) -> str:
    """Get all appointments for a student.
    
    Args:
        student_id: Student ASU ID
    
    Returns:
        JSON string with list of appointments
    """
    from agents.BookingAgent import BookingAgent
    
    booking_agent = BookingAgent()
    appointments = booking_agent.get_student_appointments(student_id)
    
    appt_list = [
        {
            "appointment_id": a.appointment_id,
            "advisor_id": a.advisor_id,
            "slot_datetime": a.slot_datetime.isoformat(),
            "status": a.status,
            "reason": a.reason
        }
        for a in appointments
    ]
    return json.dumps(appt_list)
```

#### Step 2: Create Agent with Tools

```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

def create_booking_agent(student_id: str):
    """Create a LangChain agent for booking appointments"""
    
    # Initialize LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        temperature=0.1,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    # Define all tools
    tools = [
        get_available_advisors,
        get_available_slots,
        check_slot_availability,
        book_appointment,
        get_student_appointments
    ]
    
    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful academic assistant that helps students book appointments with advisors.

Your goal is to help the student book an appointment by:
1. Understanding their program level (undergraduate or graduate)
2. Finding suitable advisors
3. Finding available time slots
4. Booking the appointment

IMPORTANT RULES:
- Always check slot availability before booking
- Appointments can only be booked for weekdays (Monday-Friday)
- Appointments must be within 30 days from today
- If a slot is unavailable, suggest alternatives
- Be conversational and helpful
- Ask clarifying questions if needed

Current student ID: {student_id}
Today's date: {today_date}"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    # Create ReAct agent
    agent = create_react_agent(llm, tools, prompt)
    
    # Create agent executor
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10
    )
    
    return executor
```

#### Step 3: Add Memory/Context Management

```python
from langchain.memory import ConversationBufferMemory
from langchain_core.chat_history import InMemoryChatMessageHistory

class BookingAgentMemory:
    """Manages conversation memory for booking agent"""
    
    def __init__(self, student_id: str):
        self.student_id = student_id
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            chat_memory=InMemoryChatMessageHistory()
        )
        self.booking_context = {
            "student_id": student_id,
            "program_level": None,
            "advisor_id": None,
            "preferred_date": None,
            "preferred_time": None
        }
    
    def add_user_message(self, message: str):
        """Add user message to memory"""
        self.memory.chat_memory.add_user_message(message)
    
    def add_ai_message(self, message: str):
        """Add AI message to memory"""
        self.memory.chat_memory.add_ai_message(message)
    
    def get_memory_variables(self):
        """Get memory variables for agent"""
        return self.memory.load_memory_variables({})
```

#### Step 4: Main Agent Execution

```python
def process_booking_request(user_input: str, student_id: str, memory: BookingAgentMemory):
    """Process booking request using LangChain agent"""
    
    # Create agent
    agent = create_booking_agent(student_id)
    
    # Get memory context
    memory_vars = memory.get_memory_variables()
    
    # Prepare input
    today = date.today().strftime("%Y-%m-%d")
    input_vars = {
        "input": user_input,
        "student_id": student_id,
        "today_date": today,
        "chat_history": memory_vars.get("chat_history", []),
        "agent_scratchpad": []
    }
    
    # Execute agent
    try:
        result = agent.invoke(input_vars)
        
        # Save to memory
        memory.add_user_message(user_input)
        memory.add_ai_message(result["output"])
        
        return {
            "success": True,
            "response": result["output"],
            "intermediate_steps": result.get("intermediate_steps", [])
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response": "I encountered an error. Please try again."
        }
```

#### Step 5: Integration with Existing System

```python
class LangChainBookingAgent:
    """LangChain-based booking agent wrapper"""
    
    def __init__(self):
        self.memories = {}  # Store memories per student
    
    def initialize_booking(self, student_id: str) -> Dict:
        """Initialize booking conversation"""
        # Create memory for student
        memory = BookingAgentMemory(student_id)
        self.memories[student_id] = memory
        
        # Initial greeting
        greeting = (
            "I'd be happy to help you book an appointment! "
            "Are you an undergraduate (BS) or graduate (MS) student?"
        )
        
        memory.add_ai_message(greeting)
        
        return {
            "success": True,
            "message": greeting,
            "booking_context": memory.booking_context
        }
    
    def process_user_message(self, user_input: str, booking_context: Dict) -> Dict:
        """Process user message in booking conversation"""
        student_id = booking_context.get("student_id")
        
        if student_id not in self.memories:
            return self.initialize_booking(student_id)
        
        memory = self.memories[student_id]
        
        # Process with LangChain agent
        result = process_booking_request(user_input, student_id, memory)
        
        # Update booking context based on agent's actions
        # (You can extract this from intermediate_steps)
        
        return {
            "success": result["success"],
            "message": result["response"],
            "booking_context": memory.booking_context,
            "state": self._determine_state(memory.booking_context)
        }
    
    def _determine_state(self, context: Dict) -> str:
        """Determine current state from context"""
        if not context.get("program_level"):
            return "need_program"
        elif not context.get("advisor_id"):
            return "need_advisor"
        elif not context.get("slot_datetime"):
            return "need_date"
        else:
            return "confirming"
```

---

### Key Advantages of LangChain Approach

1. **Autonomous Decision Making**
   - Agent decides which tools to use
   - No hardcoded state transitions
   - Handles unexpected inputs gracefully

2. **Better Error Recovery**
   - Agent can retry with different approaches
   - Can ask clarifying questions
   - Handles partial information

3. **More Natural Conversations**
   - Can handle multi-step requests: "Book me with Dr. Smith next Monday at 2 PM"
   - Can answer questions during booking: "What times are available?"
   - Can modify bookings: "Actually, change it to Tuesday"

4. **Extensibility**
   - Easy to add new tools (e.g., `reschedule_appointment`, `get_advisor_info`)
   - Can integrate with external APIs
   - Supports complex workflows

5. **Observability**
   - Can see agent's reasoning process
   - Track tool usage
   - Debug conversation flow

---

### Example Conversation Flow

**User:** "I want to book an appointment"

**Agent (thinking):**
```
Thought: User wants to book appointment. I need to:
1. Find out their program level
2. Get available advisors
3. Find available slots
4. Book the appointment

Action: I should ask about program level first.
```

**Agent:** "I'd be happy to help! Are you an undergraduate (BS) or graduate (MS) student?"

**User:** "Graduate"

**Agent (thinking):**
```
Thought: User is a graduate student. I should:
1. Get available advisors for graduate program
2. Present options to user

Action: Use get_available_advisors tool
```

**Agent:** *[Uses `get_available_advisors("graduate")`]*

**Agent:** "Here are the available advisors for graduate students:
1. Dr. Smith - Graduate Program Advisor
2. Dr. Jones - MS Program Coordinator
Which advisor would you like to meet with?"

**User:** "Dr. Smith, next Monday at 2 PM"

**Agent (thinking):**
```
Thought: User wants:
- Advisor: Dr. Smith
- Date: next Monday
- Time: 2 PM

I need to:
1. Parse "next Monday" to get actual date
2. Check if 2 PM slot is available
3. Book the appointment

Action: Use get_available_slots to find slots, then check availability
```

**Agent:** *[Uses `get_available_slots()` and `check_slot_availability()`]*

**Agent:** "Perfect! I found an available slot with Dr. Smith on Monday, March 10th at 2:00 PM. Should I book this appointment?"

**User:** "Yes"

**Agent:** *[Uses `book_appointment()`]*

**Agent:** "✅ Appointment booked successfully! Your appointment ID is abc-123. A confirmation email has been sent."

---

### Migration Strategy

1. **Phase 1: Parallel Implementation**
   - Keep existing `BookingConversationAgent`
   - Implement LangChain agent alongside
   - Test with sample conversations

2. **Phase 2: Feature Parity**
   - Ensure LangChain agent handles all current scenarios
   - Add missing tools/functionality
   - Test edge cases

3. **Phase 3: Gradual Rollout**
   - Add feature flag to switch between agents
   - Monitor performance and user satisfaction
   - Collect feedback

4. **Phase 4: Full Migration**
   - Replace `BookingConversationAgent` with LangChain agent
   - Remove old state machine code
   - Optimize and refine

---

### Additional Enhancements

1. **Structured Output**
   - Use Pydantic models for tool outputs
   - Better validation and type safety

2. **Retrieval-Augmented Booking**
   - Use RAG to answer questions during booking
   - "What does Dr. Smith specialize in?"

3. **Multi-Agent System**
   - Separate agent for cancellations
   - Separate agent for rescheduling
   - Coordinator agent to route requests

4. **Streaming Responses**
   - Real-time updates during booking
   - Show agent's thinking process

5. **Persistent Memory**
   - Store conversations in database
   - Resume conversations across sessions

---

## Summary

**Current System:**
- ✅ Works well for structured flows
- ✅ Predictable behavior
- ❌ Limited flexibility
- ❌ Hard to handle complex scenarios

**LangChain Agentic System:**
- ✅ Autonomous and flexible
- ✅ Better error handling
- ✅ More natural conversations
- ✅ Easier to extend
- ⚠️ Requires more testing
- ⚠️ Slightly more complex setup

The LangChain approach transforms your booking system from a **rigid state machine** into an **intelligent agent** that can reason about user requests and take appropriate actions autonomously.




