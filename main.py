#!/usr/bin/env python3
"""
ASU IFT Academic Assistant - Main UI
Professional chat interface for ASU Information Technology program
"""

import os
# Fix tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import streamlit as st
from dotenv import load_dotenv
from SimpleUnbiasedRAG import SimpleUnbiasedRAG
from agents.AgentController import AgentController
from agents.AuthenticationAgent import AuthenticationAgent
from services.CalendarService import CalendarService
from datetime import datetime, date, timedelta
import time

# Initialize environment
load_dotenv()

@st.cache_resource(show_spinner=False)
def init_rag_system():
    """Initialize the RAG system"""
    with st.spinner("Loading IFT Academic Assistant..."):
        rag = SimpleUnbiasedRAG()
        success = rag.load_systems()
        if not success:
            st.error("Failed to load RAG systems. Please check your API keys.")
            st.stop()
        return rag

@st.cache_resource(show_spinner=False)
def init_agent_controller():
    """Initialize Agent Controller"""
    return AgentController()

@st.cache_resource(show_spinner=False)
def init_auth_agent():
    """Initialize Authentication Agent"""
    return AuthenticationAgent()

def show_login_modal():
    """Show login modal"""
    with st.container():
        st.subheader("Login Required")
        st.write("Please login to access the Academic Assistant")
        
        asu_id = st.text_input("ASU ID", key="login_asu_id", placeholder="Enter your ASU ID")
        password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Login", type="primary", use_container_width=True):
                if asu_id and password:
                    auth_agent = init_auth_agent()
                    result = auth_agent.authenticate(asu_id, password)
                    
                    if result["success"]:
                        student = result["student"]
                        st.session_state.authenticated = True
                        st.session_state.student_id = student.asu_id
                        st.session_state.student_name = student.name
                        st.session_state.student_email = student.email
                        st.session_state.student_program = student.program_level
                        st.rerun()
                    else:
                        st.error(result["message"])
                else:
                    st.warning("Please enter both ASU ID and password")
        
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_login = False
                st.rerun()

def show_booking_flow():
    """Show 4-step booking flow"""
    controller = init_agent_controller()
    calendar_service = CalendarService()
    
    # Initialize booking state
    if "booking_step" not in st.session_state:
        st.session_state.booking_step = 1
    if "selected_program" not in st.session_state:
        st.session_state.selected_program = None
    if "selected_advisor" not in st.session_state:
        st.session_state.selected_advisor = None
    if "selected_slot" not in st.session_state:
        st.session_state.selected_slot = None
    
    st.header("Book Advising Appointment")
    st.divider()
    
    # Step 1: Program Level Selection
    if st.session_state.booking_step == 1:
        st.subheader("Step 1: Select Your Program Level")
        st.write("Are you an undergraduate or graduate student?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Undergraduate", use_container_width=True, type="primary"):
                st.session_state.selected_program = "undergraduate"
                st.session_state.booking_step = 2
                st.rerun()
        
        with col2:
            if st.button("Graduate/Master's", use_container_width=True, type="primary"):
                st.session_state.selected_program = "graduate"
                st.session_state.booking_step = 2
                st.rerun()
    
    # Step 2: Advisor Selection
    elif st.session_state.booking_step == 2:
        st.subheader("Step 2: Select Your Advisor")
        
        advisors = controller.get_available_advisors(st.session_state.selected_program)
        
        if not advisors:
            st.error("No advisors available for this program level")
            if st.button("Go Back"):
                st.session_state.booking_step = 1
                st.rerun()
        else:
            st.write(f"Select an advisor from the {st.session_state.selected_program} program:")
            
            for advisor in advisors:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{advisor['name']}**")
                        st.caption(f"{advisor['title']}")
                        st.caption(f"Email: {advisor['email']} | Phone: {advisor['phone']}")
                    with col2:
                        if st.button("Select", key=f"advisor_{advisor['advisor_id']}", use_container_width=True):
                            st.session_state.selected_advisor = advisor
                            st.session_state.booking_step = 3
                            st.rerun()
            
            if st.button("Go Back"):
                st.session_state.booking_step = 1
                st.rerun()
    
    # Step 3: Time Slot Selection
    elif st.session_state.booking_step == 3:
        st.subheader("Step 3: Select Date and Time")
        
        if not st.session_state.selected_advisor:
            st.error("No advisor selected")
            st.session_state.booking_step = 2
            st.rerun()
        
        advisor_id = st.session_state.selected_advisor['advisor_id']
        advisor_name = st.session_state.selected_advisor['name']
        
        st.write(f"Select a time slot for **{advisor_name}**")
        
        # Date selection
        min_date = date.today() + timedelta(days=1)
        max_date = date.today() + timedelta(days=30)
        
        selected_date = st.date_input(
            "Select Date",
            min_value=min_date,
            max_value=max_date,
            value=min_date,
            key="booking_date"
        )
        
        # Get available slots for selected date
        end_date = selected_date
        available_slots = controller.booking_agent.get_available_slots(advisor_id, selected_date, end_date)
        
        # Filter slots for selected date only
        selected_date_slots = [slot for slot in available_slots if slot.date() == selected_date]
        
        if not selected_date_slots:
            st.warning(f"No available slots on {selected_date.strftime('%A, %B %d, %Y')}. Please select another date.")
        else:
            st.write(f"Available time slots on {selected_date.strftime('%A, %B %d, %Y')}:")
            
            # Display slots in a grid
            cols = st.columns(3)
            for idx, slot in enumerate(selected_date_slots):
                col_idx = idx % 3
                time_str = calendar_service.format_slot_time_only(slot)
                if cols[col_idx].button(
                    time_str,
                    key=f"slot_{slot.isoformat()}",
                    use_container_width=True
                ):
                    st.session_state.selected_slot = slot
                    st.session_state.booking_step = 4
                    st.rerun()
        
        if st.button("Go Back"):
            st.session_state.booking_step = 2
            st.rerun()
    
    # Step 4: Confirmation
    elif st.session_state.booking_step == 4:
        st.subheader("Step 4: Confirm Appointment")
        
        if not all([st.session_state.selected_program, st.session_state.selected_advisor, st.session_state.selected_slot]):
            st.error("Missing booking information")
            st.session_state.booking_step = 1
            st.rerun()
        
        advisor = st.session_state.selected_advisor
        slot = st.session_state.selected_slot
        
        # Display booking summary
        st.write("**Appointment Summary:**")
        st.write(f"- **Advisor:** {advisor['name']}")
        st.write(f"- **Date:** {slot.strftime('%A, %B %d, %Y')}")
        st.write(f"- **Time:** {calendar_service.format_slot_time_only(slot)}")
        st.write(f"- **Location:** {advisor.get('office_location', 'Sutton Hall')}")
        
        # Optional reason
        reason = st.text_area("Reason for appointment (optional)", key="booking_reason", height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm Booking", type="primary", use_container_width=True):
                # Book appointment
                with st.spinner("Booking appointment..."):
                    result = controller.process_booking_flow(
                        student_id=st.session_state.student_id,
                        advisor_id=advisor['advisor_id'],
                        slot_datetime=slot,
                        reason=reason if reason.strip() else None
                    )
                    
                    if result["success"]:
                        st.success("Appointment booked successfully!")
                        st.write(f"**Appointment ID:** {result['appointment'].appointment_id}")
                        
                        if result.get("email_sent"):
                            st.info("Confirmation email sent to your email address")
                        elif result.get("email_note"):
                            st.info(result["email_note"])
                        
                        # Reset booking state
                        st.session_state.booking_step = 1
                        st.session_state.selected_program = None
                        st.session_state.selected_advisor = None
                        st.session_state.selected_slot = None
                        st.session_state.show_booking = False
                        
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"Booking failed: {result['message']}")
        
        with col2:
            if st.button("Go Back", use_container_width=True):
                st.session_state.booking_step = 3
                st.rerun()
    
    # Cancel booking button
    st.divider()
    if st.button("Cancel Booking", use_container_width=True):
        st.session_state.booking_step = 1
        st.session_state.selected_program = None
        st.session_state.selected_advisor = None
        st.session_state.selected_slot = None
        st.session_state.show_booking = False
        st.rerun()

def main():
    st.set_page_config(
        page_title="IFT Academic Assistant", 
        page_icon=None, 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize systems
    rag_system = init_rag_system()
    controller = init_agent_controller()
    
    # Initialize session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "show_login" not in st.session_state:
        st.session_state.show_login = False
    if "show_booking" not in st.session_state:
        st.session_state.show_booking = False
    
    # Sidebar - Student Information
    with st.sidebar:
        st.header("Student Information")
        
        if st.session_state.authenticated:
            # Show authenticated student info
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image("https://via.placeholder.com/60x60/4A90E2/FFFFFF?text=JD", width=60)
            with col2:
                st.write(f"**{st.session_state.student_name}**")
                st.caption(f"ASU ID: {st.session_state.student_id}")
                st.caption(f"{st.session_state.student_email}")
            
            st.success("Authentication Successful")
            st.info(f"Program: {st.session_state.student_program.title()}")
            
            if st.button("Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.student_id = None
                st.session_state.student_name = None
                st.session_state.student_email = None
                st.session_state.student_program = None
                st.rerun()
        else:
            # Show login prompt
            st.info("Not logged in")
            if st.button("Login", type="primary", use_container_width=True):
                st.session_state.show_login = True
                st.rerun()
        
        st.divider()
        
        # Quick Actions
        st.header("Quick Actions")
        if st.button("Book Appointment", use_container_width=True, type="primary"):
            if st.session_state.authenticated:
                st.session_state.show_booking = True
                st.session_state.booking_step = 1
                st.rerun()
            else:
                st.session_state.show_login = True
                st.rerun()
        
        st.divider()
        
        # Chat History Section
        st.header("Chat History")
        
        if st.session_state.chat_history:
            for i, message in enumerate(st.session_state.chat_history[-5:]):
                if message["role"] == "user":
                    st.markdown(f"""
                    <div style="
                        background-color: #f0f2f6; 
                        padding: 8px 12px; 
                        border-radius: 18px; 
                        margin: 4px 0;
                        font-size: 14px;
                    ">{message['content'][:50]}{'...' if len(message['content']) > 50 else ''}</div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No chat history yet")
        
        st.divider()
        
        # Example Questions Section
        st.header("Example Questions")
        
        example_questions = [
            "what are graduation requirements for MS in IT?",
            "What are the specializations in B.S in information technology?",
            "How do I apply for the capstone project?"
        ]
        
        for question in example_questions:
            if st.button(question, key=f"example_{question}", use_container_width=True):
                st.session_state.current_question = question
                st.rerun()
    
    # Main Content Area
    # Show login modal if needed
    if st.session_state.show_login:
        show_login_modal()
        return
    
    # Show booking flow if active
    if st.session_state.show_booking:
        show_booking_flow()
        return
    
    # Normal chat interface
    col_title, col_book = st.columns([3, 1])
    with col_title:
        st.title("IFT Academic Assistant")
        st.caption("Ask questions about IFT program details, courses, and academic tasks.")
    with col_book:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Book Appointment", type="primary", use_container_width=True):
            if st.session_state.authenticated:
                st.session_state.show_booking = True
                st.session_state.booking_step = 1
                st.rerun()
            else:
                st.session_state.show_login = True
                st.rerun()
    
    st.divider()
    
    # Chat Interface
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(f"""
            <div style="
                display: flex; 
                justify-content: flex-start; 
                margin: 10px 0;
            ">
                <div style="
                    background-color: #f0f2f6; 
                    padding: 12px 16px; 
                    border-radius: 18px; 
                    max-width: 70%;
                    font-size: 14px;
                ">{message['content']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        elif message["role"] == "assistant":
            response_text = message['content']
            
            st.markdown(f"""
            <div style="
                display: flex; 
                justify-content: flex-end; 
                margin: 10px 0;
            ">
                <div style="
                    background-color: #1f2937; 
                    color: white;
                    padding: 12px 16px; 
                    border-radius: 18px; 
                    max-width: 70%;
                    font-size: 14px;
                ">{response_text}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if "sources" in message and message["sources"]:
                with st.expander("Sources"):
                    for i, source in enumerate(message["sources"][:3], 1):
                        if hasattr(source, 'page_content'):
                            snippet = source.page_content[:200] + ("..." if len(source.page_content) > 200 else "")
                            st.write(f"**Source {i}:** {snippet}")
                        else:
                            st.write(f"**Source {i}:** {str(source)[:200]}...")
    
    # Chat Input
    st.markdown("<br>", unsafe_allow_html=True)
    
    if "current_question" in st.session_state:
        default_question = st.session_state.current_question
        del st.session_state.current_question
    else:
        default_question = ""
    
    col1, col2 = st.columns([5, 1])
    
    with col1:
        user_input = st.text_input(
            "Ask your question",
            value=default_question,
            placeholder="Ask about IFT program details or book advising appointment...",
            label_visibility="collapsed"
        )
    
    with col2:
        send_button = st.button("Send", type="primary", use_container_width=True)
    
    # Process user input
    if send_button and user_input.strip():
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Route request using Agent Controller
        student_context = None
        if st.session_state.authenticated:
            student_context = {
                "authenticated": True,
                "asu_id": st.session_state.student_id,
                "program_level": st.session_state.student_program
            }
        
        route_result = controller.route_request(user_input, student_context)
        
        if route_result["intent"] == "booking":
            if route_result["action"] == "require_authentication":
                st.session_state.show_login = True
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "Please login to book an appointment. Click the 'Login' button in the sidebar."
                })
                st.rerun()
            elif route_result["action"] == "start_booking":
                st.session_state.show_booking = True
                st.session_state.booking_step = 1
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "Starting appointment booking process. Please follow the steps to book your appointment."
                })
                st.rerun()
        else:
            # Question intent - use RAG system
            with st.spinner("Processing your question..."):
                try:
                    start_time = time.time()
                    result = rag_system.ask(user_input)
                    response_time = time.time() - start_time
                    
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result.get("docs", []),
                        "time": response_time
                    })
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.info("Please try again or check your internet connection")
    
    # Footer
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 12px;'>
        <p><strong>ASU Polytechnic School - Information Technology Program</strong></p>
        <p>Academic Assistant</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Performance stats in sidebar
    with st.sidebar:
        if st.button("Show Performance Stats"):
            if rag_system.stats["total_queries"] > 0:
                st.subheader("System Statistics")
                st.metric("Total Queries", rag_system.stats["total_queries"])
                st.info("Using Gemini model")
            else:
                st.info("No queries yet")

if __name__ == "__main__":
    main()
