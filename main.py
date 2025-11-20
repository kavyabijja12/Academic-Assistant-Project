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
import re
import time
from datetime import datetime, date, timedelta
from SimpleUnbiasedRAG import SimpleUnbiasedRAG
from agents.AgentController import AgentController
from agents.AuthenticationAgent import AuthenticationAgent
from services.CalendarService import CalendarService

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

# Removed show_booking_flow() - now using conversational booking in chat

def main():
    st.set_page_config(
        page_title="IFT Academic Assistant", 
        page_icon="🎓", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Add custom CSS for better styling
    st.markdown("""
    <style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Button improvements */
    .stButton > button {
        border-radius: 10px;
        font-weight: 500;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
    }
    
    /* Header improvements */
    h1 {
        color: #1e3c72;
        font-weight: 700;
    }
    
    /* Divider styling */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
        margin: 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
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
    if "booking_context" not in st.session_state:
        st.session_state.booking_context = None
    if "booking_in_progress" not in st.session_state:
        st.session_state.booking_in_progress = False
    
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
        st.markdown("### ⚡ Quick Actions")
        book_button = st.button("📅 Book Appointment", use_container_width=True, type="primary")
        if book_button:
            if st.session_state.authenticated:
                # Initialize conversational booking (always ask for program level first)
                init_result = controller.initialize_booking_conversation(
                    st.session_state.student_id,
                    None  # Always ask for program level (MS or BS)
                )
                st.session_state.booking_context = init_result["booking_context"]
                st.session_state.booking_in_progress = True
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": init_result["message"]
                })
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
            "How do I apply for the applied project?"
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
    
    # Normal chat interface with improved header
    col_title, col_book = st.columns([3, 1])
    with col_title:
        st.markdown("""
        <div style="margin-bottom: 10px;">
            <h1 style="margin: 0; color: #1e3c72;">🎓 IFT Academic Assistant</h1>
            <p style="color: #666; margin-top: 5px; font-size: 16px;">
                Ask questions about IFT program details, courses, and academic tasks.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with col_book:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📅 Book Appointment", type="primary", use_container_width=True):
            if st.session_state.authenticated:
                # Initialize conversational booking (always ask for program level first)
                init_result = controller.initialize_booking_conversation(
                    st.session_state.student_id,
                    None  # Always ask for program level (MS or BS)
                )
                st.session_state.booking_context = init_result["booking_context"]
                st.session_state.booking_in_progress = True
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": init_result["message"]
                })
                st.rerun()
            else:
                st.session_state.show_login = True
                st.rerun()
    
    st.divider()
    
    # Show booking status indicator if booking in progress
    if st.session_state.booking_in_progress:
        st.info("🔄 **Booking in progress...** Please complete the booking conversation below.")
        st.markdown("---")
    
    # Chat Interface
    for idx, message in enumerate(st.session_state.chat_history):
        if message["role"] == "user":
            st.markdown(f"""
            <div style="
                display: flex; 
                justify-content: flex-start; 
                margin: 15px 0;
                padding: 0 10px;
            ">
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 14px 18px; 
                    border-radius: 20px 20px 20px 4px; 
                    max-width: 75%;
                    font-size: 15px;
                    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
                    line-height: 1.5;
                ">{message['content']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        elif message["role"] == "assistant":
            response_text = message['content']
            
            # Skip showing the message if we're about to show clickable options
            # This prevents redundant information display
            show_message = True
            if (st.session_state.booking_in_progress and 
                st.session_state.booking_context and 
                isinstance(st.session_state.booking_context, dict)):
                booking_ctx = st.session_state.booking_context
                
                # Check if this message contains advisor list patterns
                has_advisor_list = (
                    "Here are the available advisors" in response_text or
                    "Which advisor would you like to meet" in response_text or
                    (len(response_text) > 200 and "advisor" in response_text.lower() and "@asu.edu" in response_text)
                )
                
                # Check if this message contains time slot list patterns
                has_time_list = (
                    "Here are the available times" in response_text or
                    "Here are the available slots" in response_text or
                    "available time slots" in response_text or
                    (len(response_text) > 150 and "•" in response_text and ("PM" in response_text or "AM" in response_text))
                )
                
                # Check if this message contains date list patterns
                has_date_list = (
                    "Here are some alternative dates" in response_text or
                    "alternative dates with available slots" in response_text
                )
                
                # Don't show the message if we have clickable options to show
                if (booking_ctx.get("state") == "need_advisor" and booking_ctx.get("available_advisors") and has_advisor_list) or \
                   (booking_ctx.get("state") == "need_time" and booking_ctx.get("available_slots") and has_time_list) or \
                   (booking_ctx.get("state") == "need_date" and booking_ctx.get("suggested_dates") and has_date_list):
                    show_message = False  # Hide long lists since we show cards
                elif (booking_ctx.get("state") == "need_advisor" and booking_ctx.get("available_advisors")) or \
                     (booking_ctx.get("state") == "need_time" and booking_ctx.get("available_slots")) or \
                     (booking_ctx.get("state") == "need_date" and booking_ctx.get("suggested_dates")):
                    # Show short messages only
                    if len(response_text) < 100:
                        show_message = True
                    else:
                        show_message = False
            
            if show_message:
                # Convert markdown-style formatting to HTML properly
                # Convert **text** to <strong>text</strong>
                response_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', response_text)
                # Convert newlines to <br>
                response_text = response_text.replace('\n', '<br>')
            
            st.markdown(f"""
            <div style="
                display: flex; 
                justify-content: flex-end; 
                    margin: 15px 0;
                    padding: 0 10px;
            ">
                <div style="
                        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    color: white;
                        padding: 14px 18px; 
                        border-radius: 20px 20px 4px 20px; 
                        max-width: 75%;
                        font-size: 15px;
                        box-shadow: 0 2px 8px rgba(30, 60, 114, 0.3);
                        line-height: 1.6;
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
    
    # Show clickable options ONCE after all messages (not in the loop)
    if (st.session_state.booking_in_progress and 
        st.session_state.booking_context and 
        isinstance(st.session_state.booking_context, dict)):
        booking_ctx = st.session_state.booking_context
        
        # Show advisor selection cards
        if booking_ctx.get("state") == "need_advisor" and booking_ctx.get("available_advisors"):
            advisors = booking_ctx["available_advisors"]
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 👤 Select an Advisor")
            st.markdown("---")
            
            # Display advisors in cards - 2 columns
            num_cols = 2
            cols = st.columns(num_cols)
            
            for i, advisor in enumerate(advisors[:6]):  # Show max 6 advisors
                col_idx = i % num_cols
                with cols[col_idx]:
                    # Advisor card
                    st.markdown(f"""
                    <div style="
                        border: 2px solid #667eea;
                        border-radius: 12px;
                        padding: 20px;
                        margin-bottom: 15px;
                        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                        box-shadow: 0 4px 6px rgba(102, 126, 234, 0.1);
                    ">
                        <h4 style="margin: 0 0 10px 0; color: #1e3c72; font-size: 18px;">{advisor["name"]}</h4>
                        <p style="margin: 0 0 8px 0; color: #666; font-size: 14px; font-weight: 500;">{advisor.get("title", "Advisor")}</p>
                        <p style="margin: 0; color: #888; font-size: 13px;">📧 {advisor["email"]}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Select button
                    if st.button(
                        f"Select {advisor['name'].split()[0]}",
                        key=f"advisor_btn_{i}",
                        use_container_width=True,
                        type="primary"
                    ):
                        # Process advisor selection
                        result = controller.process_booking_message(
                            advisor["name"],
                            booking_ctx
                        )
                        st.session_state.booking_context = result["booking_context"]
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": result["message"]
                        })
                        if result["state"] == "complete":
                            st.session_state.booking_in_progress = False
                            st.session_state.booking_context = None
                        st.rerun()
        
        # Show alternative date buttons when no slots available
        elif booking_ctx.get("state") == "need_date" and booking_ctx.get("suggested_dates"):
            suggested_dates = booking_ctx["suggested_dates"]
            if suggested_dates and len(suggested_dates) > 0:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### 📅 Select an Alternative Date")
                st.markdown("---")
                
                num_cols = min(3, len(suggested_dates))
                cols = st.columns(num_cols if num_cols > 0 else 1)
                for i, alt_date in enumerate(suggested_dates[:6]):  # Show max 6 dates
                    if alt_date and hasattr(alt_date, 'strftime'):
                        col_idx = i % num_cols if num_cols > 0 else 0
                        date_str = alt_date.strftime("%b %d")
                        day_name = alt_date.strftime("%A")
                        
                        with cols[col_idx]:
                            st.markdown(f"""
                            <div style="
                                border: 2px solid #4CAF50;
                                border-radius: 10px;
                                padding: 12px;
                                margin-bottom: 10px;
                                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                                text-align: center;
                            ">
                                <div style="font-weight: bold; color: #2d5016; font-size: 16px;">{day_name}</div>
                                <div style="color: #1e3c72; font-size: 18px; margin: 5px 0;">{date_str}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button(
                                f"Select {date_str}",
                                key=f"date_btn_{i}",
                                use_container_width=True,
                                type="primary"
                            ):
                                # Process date selection
                                date_input = alt_date.strftime("%B %d")
                                result = controller.process_booking_message(
                                    date_input,
                                    booking_ctx
                                )
                                st.session_state.booking_context = result["booking_context"]
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "content": result["message"]
                                })
                                if result["state"] == "complete":
                                    st.session_state.booking_in_progress = False
                                    st.session_state.booking_context = None
                                st.rerun()
        
        # Show time slot selection buttons grouped by date
        elif booking_ctx.get("state") == "need_time" and booking_ctx.get("available_slots"):
            slots = booking_ctx["available_slots"]
            
            # Group slots by date
            from collections import defaultdict
            slots_by_date = defaultdict(list)
            for slot in slots:
                slot_date = slot.date()
                slots_by_date[slot_date].append(slot)
            
            # Sort dates
            sorted_dates = sorted(slots_by_date.keys())
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### ⏰ Select a Time Slot")
            st.markdown("---")
            
            # Display slots grouped by date
            for date_obj in sorted_dates:
                date_slots = sorted(slots_by_date[date_obj])
                date_str = date_obj.strftime("%A, %B %d, %Y")
                
                st.markdown(f"#### 📅 {date_str}")
                st.markdown("---")
                
                # Display time slots for this date in a grid
                cols = st.columns(4)  # 4 columns for better layout
                for i, slot in enumerate(date_slots[:16]):  # Max 16 slots per date
                    col_idx = i % 4
                    time_str = CalendarService().format_slot_time_only(slot)
                    
                    with cols[col_idx]:
                        if st.button(
                            time_str,
                            key=f"slot_btn_{date_obj}_{i}",
                            use_container_width=True,
                            type="primary"
                        ):
                            # Process time selection
                            result = controller.process_booking_message(
                                slot.isoformat(),
                                booking_ctx
                            )
                            st.session_state.booking_context = result["booking_context"]
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": result["message"]
                            })
                            if result["state"] == "complete":
                                st.session_state.booking_in_progress = False
                                st.session_state.booking_context = None
                            st.rerun()
                
                st.markdown("<br>", unsafe_allow_html=True)  # Space between dates
    
    # Chat Input
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Initialize chat input value if not exists
    if "chat_input_value" not in st.session_state:
        st.session_state.chat_input_value = ""
    
    # Handle example question clicks
    if "current_question" in st.session_state:
        st.session_state.chat_input_value = st.session_state.current_question
        del st.session_state.current_question
    
    # Use form to handle input clearing properly
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        
        with col1:
            placeholder_text = "💬 Ask about IFT program details or book advising appointment..."
            if st.session_state.booking_in_progress:
                placeholder_text = "💬 Continue your booking conversation..."
            
            user_input = st.text_input(
                "Ask your question",
                value=st.session_state.chat_input_value,
                placeholder=placeholder_text,
                label_visibility="collapsed"
            )
        
        with col2:
            send_button = st.form_submit_button("📤 Send", type="primary", use_container_width=True)
        
        # Process user input
        if send_button and user_input.strip():
            # Store the input before form clears it
            input_text = user_input.strip()
            # Clear the session state value for next interaction
            st.session_state.chat_input_value = ""
            st.session_state.chat_history.append({
                "role": "user",
                "content": input_text
            })
            
            # Check if booking conversation is in progress
            if st.session_state.booking_in_progress and st.session_state.booking_context:
                # Process booking conversation message
                with st.spinner("Processing..."):
                    result = controller.process_booking_message(
                        input_text,
                        st.session_state.booking_context
                    )
                    
                    st.session_state.booking_context = result["booking_context"]
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": result["message"]
                    })
                    
                    # Check if booking is complete or cancelled
                    if result["state"] in ["complete", "cancelled"]:
                        st.session_state.booking_in_progress = False
                        if result["state"] == "complete":
                            st.session_state.booking_context = None
                    
                    # Input already cleared above, just rerun
                    st.rerun()
            else:
                # Route request using Agent Controller
                student_context = None
                if st.session_state.authenticated:
                    student_context = {
                        "authenticated": True,
                        "asu_id": st.session_state.student_id,
                        "program_level": st.session_state.student_program
                    }
                
                route_result = controller.route_request(input_text, student_context)
                
                if route_result["intent"] == "booking":
                    if route_result["action"] == "require_authentication":
                        st.session_state.show_login = True
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": "Please login to book an appointment. Click the 'Login' button in the sidebar."
                        })
                        # Input already cleared above
                        st.rerun()
                    elif route_result["action"] == "start_booking":
                        # Initialize conversational booking (always ask for program level first)
                        init_result = controller.initialize_booking_conversation(
                            student_context["asu_id"],
                            None  # Always ask for program level (MS or BS)
                        )
                        st.session_state.booking_context = init_result["booking_context"]
                        st.session_state.booking_in_progress = True
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": init_result["message"]
                        })
                        # Input already cleared above
                        st.rerun()
                else:
                    # Question intent - use RAG system
                    with st.spinner("Processing your question..."):
                        try:
                            start_time = time.time()
                            result = rag_system.ask(input_text)
                            response_time = time.time() - start_time
                            
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": result["answer"],
                                "sources": result.get("docs", []),
                                "time": response_time
                            })
                            
                            # Input already cleared above, just rerun
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
