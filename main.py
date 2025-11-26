#!/usr/bin/env python3
"""
ASU IFT Academic Assistant - Main UI
Updated: uses labeled 'Send' submit and more robust styling to avoid red button
"""

import os
import re
import time
import sqlite3
from collections import defaultdict

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# These imports are placeholders; keep your original modules
from SimpleUnbiasedRAG import SimpleUnbiasedRAG
from agents.AgentController import AgentController
from agents.AuthenticationAgent import AuthenticationAgent
from services.CalendarService import CalendarService

# Fix tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"
load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history.db")


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def init_chat_history_db():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asu_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            intent_category TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Add intent_category column if it doesn't exist (for existing databases)
    try:
        conn.execute("ALTER TABLE chat_messages ADD COLUMN intent_category TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            asu_id TEXT PRIMARY KEY,
            student_name TEXT NOT NULL,
            student_email TEXT NOT NULL,
            student_program TEXT NOT NULL,
            last_login DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_message_to_db(asu_id: str, role: str, content: str, intent_category: str = None):
    if not asu_id:
        return
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO chat_messages (asu_id, role, content, intent_category) VALUES (?, ?, ?, ?)",
        (asu_id, role, content, intent_category),
    )
    conn.commit()
    conn.close()


def load_recent_messages_from_db(asu_id: str, limit: int = 50):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT role, content
        FROM chat_messages
        WHERE asu_id = ?
        ORDER BY timestamp DESC, id DESC
        LIMIT ?
        """,
        (asu_id, limit),
    ).fetchall()
    conn.close()
    messages = [{"role": row[0], "content": row[1]} for row in rows]
    messages.reverse()
    return messages


def save_user_session(asu_id: str, student_name: str, student_email: str, student_program: str):
    """Save user session to database"""
    conn = get_db_connection()
    conn.execute(
        """
        INSERT OR REPLACE INTO user_sessions (asu_id, student_name, student_email, student_program, last_login)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (asu_id, student_name, student_email, student_program),
    )
    conn.commit()
    conn.close()


def load_user_session(asu_id: str):
    """Load user session from database"""
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT student_name, student_email, student_program
        FROM user_sessions
        WHERE asu_id = ?
        """,
        (asu_id,),
    ).fetchone()
    conn.close()
    if row:
        return {
            "student_name": row[0],
            "student_email": row[1],
            "student_program": row[2],
        }
    return None


def clear_user_session(asu_id: str):
    """Clear user session from database"""
    conn = get_db_connection()
    conn.execute("DELETE FROM user_sessions WHERE asu_id = ?", (asu_id,))
    conn.commit()
    conn.close()


def get_most_recent_session():
    """Get the most recent user session from database"""
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT asu_id, student_name, student_email, student_program
        FROM user_sessions
        ORDER BY last_login DESC
        LIMIT 1
        """
    ).fetchone()
    conn.close()
    if row:
        return {
            "asu_id": row[0],
            "student_name": row[1],
            "student_email": row[2],
            "student_program": row[3],
        }
    return None


def restore_user_session():
    """Restore user session from database on app load"""
    if st.session_state.get("session_restored"):
        return
    
    session = get_most_recent_session()
    if session:
        st.session_state.authenticated = True
        st.session_state.student_id = session["asu_id"]
        st.session_state.student_name = session["student_name"]
        st.session_state.student_email = session["student_email"]
        st.session_state.student_program = session["student_program"]
        st.session_state.session_restored = True
        # Don't load old messages into chat_history - keep main chat area fresh
        # Old messages will be shown in sidebar from DB directly


def add_chat_message(role: str, content: str, skip_db_save: bool = False, intent_category: str = None, **extras):
    """
    Add a message to chat history
    
    Args:
        role: Message role ("user" or "assistant")
        content: Message content
        skip_db_save: If True, don't save to database (for intermediate booking messages)
        intent_category: Category of the message ("booking" or "question")
        **extras: Additional message metadata
    """
    message = {"role": role, "content": content}
    for key, value in extras.items():
        if value is not None:
            message[key] = value
    st.session_state.chat_history.append(message)
    # Only save to DB if not skipped and user is authenticated
    if not skip_db_save and st.session_state.get("authenticated") and st.session_state.get("student_id"):
        save_message_to_db(st.session_state.student_id, role, content, intent_category)


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


def get_custom_styles():
    """Return custom CSS and JavaScript for styling - robust and targets 'Send' submit"""
    return """
    <style>
    /* ---------- GLOBAL LAYOUT ---------- */
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    [data-testid="stSidebar"] { background: white; }

    /* ---------- Remove outer form visuals ---------- */
    div[data-testid="stForm"], form[data-testid="stForm"], .element-container { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; margin: 0 !important; }

    /* ---------- Input style ---------- */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #000;
        background: white;
        color: #000;
        font-size: 15px !important;
        padding: 10px 14px !important;
    }

    /* ---------- Generic buttons ---------- */
    .stButton > button { border-radius: 8px; font-weight: 400; border: 1px solid #000; background: white; color: #000; }
    .stButton > button:hover { background: #000; color: white; }

    /* ---------- Strong send button override (targets submit buttons, aria-label Send, & text 'Send') ---------- */

    /* target submit buttons */
    form button[type="submit"],
    form input[type="submit"],
    [data-testid="stForm"] button[type="submit"],
    [data-testid="stForm"] input[type="submit"] {
        background-image: none !important;
        background: #4a4a4a !important;
        background-color: #4a4a4a !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        min-width: 52px !important;
        width: 52px !important;
        height: 40px !important;
        font-size: 15px !important;
        padding: 0 10px !important;
        box-shadow: none !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* target buttons with aria-label = Send (Streamlit usually sets aria-label) */
    button[aria-label="Send"],
    button[aria-label="send"],
    input[aria-label="Send"],
    input[aria-label="send"] {
        background-image: none !important;
        background: #4a4a4a !important;
        color: #fff !important;
        border: none !important;
        border-radius: 6px !important;
    }

    /* If the button renders an SVG icon, force the icon fill to white */
    button[type="submit"] svg, button[type="submit"] path,
    input[type="submit"] svg, input[type="submit"] path {
        fill: #ffffff !important;
        color: #ffffff !important;
    }

    /* extra override for any inline gradient */
    button[style*="linear-gradient"], button[style*="radial-gradient"],
    input[style*="linear-gradient"], input[style*="radial-gradient"] {
        background-image: none !important;
        background: #4a4a4a !important;
    }

    /* Book / Login primary style */
    .stButton > button[kind="primary"], button[kind="primary"], [data-baseweb="button"][kind="primary"] {
        background: #4a4a4a !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
    }

    </style>

    <script>
    (function ensureSendStyled() {
        // Force-style send candidates by attribute / text / svg-only
        const forced = {
            'background': '#4a4a4a',
            'background-color': '#4a4a4a',
            'color': '#ffffff',
            'border': 'none',
            'border-radius': '6px',
            'padding': '0 10px',
            'min-width': '52px',
            'height': '40px',
            'font-size': '15px',
            'display': 'inline-flex',
            'align-items': 'center',
            'justify-content': 'center',
            'box-shadow': 'none'
        };

        function apply(el) {
            if (!el || !(el instanceof HTMLElement)) return;
            try {
                Object.entries(forced).forEach(([k,v]) => el.style.setProperty(k, v, 'important'));
                // force svg/path fills white
                el.querySelectorAll('svg, path').forEach(s => {
                    try { s.style.setProperty('fill', '#ffffff', 'important'); s.setAttribute('fill', '#ffffff'); } catch(e) {}
                });
            } catch(e){}
        }

        function looksLikeSend(el) {
            if (!el || !(el instanceof HTMLElement)) return false;
            if (el.getAttribute('type') === 'submit') return true;
            // aria-label
            const aria = (el.getAttribute('aria-label') || '').toLowerCase();
            if (aria === 'send' || aria === 'submit') return true;
            // text content (trim)
            const text = (el.textContent || '').trim();
            if (text === 'Send' || text === 'send' || text === 'Submit') return true;
            // contains only an SVG and no text
            const hasSVG = !!el.querySelector('svg');
            if (hasSVG && !text) return true;
            return false;
        }

        function findAllAndApply() {
            const nodes = Array.from(document.querySelectorAll('button, input[type="submit"], [data-baseweb="button"]'));
            nodes.forEach(n => {
                try {
                    if (looksLikeSend(n)) apply(n);
                } catch(e){}
            });
        }

        // initial
        findAllAndApply();

        // observe
        const obs = new MutationObserver(() => setTimeout(findAllAndApply, 8));
        obs.observe(document.body, { childList: true, subtree: true, attributes: true });

        // periodic fallback
        setInterval(findAllAndApply, 700);

        // reapply on visibility
        document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') findAllAndApply(); }, false);
    })();
    </script>
    """


def show_login_modal():
    """Show student login modal"""
    with st.container():
        st.subheader("Student Login")
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
                        # Save session to database
                        save_user_session(student.asu_id, student.name, student.email, student.program_level)
                        # Don't load old messages into chat_history - keep main chat area fresh
                        # Old messages will be shown in sidebar from DB directly
                        st.session_state.session_restored = True
                        st.session_state.show_login = False
                        st.rerun()
                    else:
                        st.error(result["message"])
                else:
                    st.warning("Please enter both ASU ID and password")
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_login = False
                st.rerun()


def show_admin_login_modal():
    """Show admin login modal"""
    with st.container():
        st.subheader("Admin Login")
        st.write("Please login to access the Admin Dashboard")
        
        admin_id = st.text_input("Admin ID", key="admin_login_id", placeholder="Enter your Admin ID or Email")
        password = st.text_input("Password", type="password", key="admin_login_password", placeholder="Enter your password")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Login", type="primary", use_container_width=True, key="admin_login_btn"):
                if admin_id and password:
                    auth_agent = init_auth_agent()
                    result = auth_agent.authenticate_admin(admin_id, password)
                    if result["success"]:
                        admin = result["admin"]  # This should be a dictionary
                        # Handle both dict and object cases for safety
                        if isinstance(admin, dict):
                            st.session_state.admin_authenticated = True
                            st.session_state.admin_id = admin["admin_id"]
                            st.session_state.admin_name = admin["name"]
                            st.session_state.admin_email = admin["email"]
                        else:
                            # Fallback if it's still an object (shouldn't happen, but just in case)
                            st.session_state.admin_authenticated = True
                            st.session_state.admin_id = admin.admin_id
                            st.session_state.admin_name = admin.name
                            st.session_state.admin_email = admin.email
                        st.session_state.show_admin_login = False
                        st.rerun()
                    else:
                        st.error(result["message"])
                else:
                    st.warning("Please enter both Admin ID and password")
        with col2:
            if st.button("Cancel", use_container_width=True, key="admin_cancel_btn"):
                st.session_state.show_admin_login = False
                st.rerun()


def initialize_session_state():
    defaults = {
        "chat_history": [],
        "authenticated": False,
        "admin_authenticated": False,
        "show_login": False,
        "show_admin_login": False,
        "show_admin_dashboard": False,
        "booking_context": None,
        "booking_in_progress": False,
        "chat_input_value": "",
        "history_loaded": False,
        "session_restored": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    
    # Restore session from database if not already restored (only for students)
    if not st.session_state.get("session_restored") and not st.session_state.get("admin_authenticated"):
        restore_user_session()


def render_user_message(message):
    st.markdown(f"""
    <div style="display:flex;justify-content:flex-start;margin:15px 0;padding:0 10px;">
      <div style="background:#e5e5e5;color:#000;padding:14px 18px;border-radius:20px 20px 20px 4px;max-width:75%;font-size:15px;box-shadow:0 2px 4px rgba(0,0,0,0.1);">{message['content']}</div>
    </div>
    """, unsafe_allow_html=True)


def render_assistant_message(message):
    response_text = message['content']
    response_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', response_text)
    response_text = response_text.replace('\n', '<br>')
    st.markdown(f"""
    <div style="display:flex;justify-content:flex-end;margin:15px 0;padding:0 10px;">
      <div style="background:#4a4a4a;color:white;padding:14px 18px;border-radius:20px 20px 4px 20px;max-width:75%;font-size:15px;box-shadow:0 2px 4px rgba(0,0,0,0.2);">{response_text}</div>
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


def should_show_message(response_text, booking_ctx):
    if not (st.session_state.booking_in_progress and booking_ctx and isinstance(booking_ctx, dict)):
        return True
    has_advisor_list = ("Here are the available advisors" in response_text or "Which advisor would you like to meet" in response_text or (len(response_text) > 200 and "advisor" in response_text.lower() and "@asu.edu" in response_text))
    has_time_list = ("Here are the available times" in response_text or "Here are the available slots" in response_text or "available time slots" in response_text or (len(response_text) > 150 and "•" in response_text and ("PM" in response_text or "AM" in response_text)))
    has_date_list = ("Here are some alternative dates" in response_text or "alternative dates with available slots" in response_text)
    has_program_question = ("Are you an undergraduate" in response_text or "undergraduate (BS) or graduate (MS)" in response_text)
    state = booking_ctx.get("state")
    if (state == "need_program" and has_program_question) or (state == "need_advisor" and booking_ctx.get("available_advisors") and has_advisor_list) or (state == "need_time" and booking_ctx.get("available_slots") and has_time_list) or (state == "need_date" and booking_ctx.get("suggested_dates") and has_date_list):
        return False
    if (state == "need_advisor" and booking_ctx.get("available_advisors")) or (state == "need_time" and booking_ctx.get("available_slots")) or (state == "need_date" and booking_ctx.get("suggested_dates")) or (state == "need_program"):
        return len(response_text) < 100
    return True


def render_sidebar(rag_system):
    st.header("Student Information")
    if st.session_state.authenticated:
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
            # Clear session from database
            if st.session_state.student_id:
                clear_user_session(st.session_state.student_id)
            st.session_state.authenticated = False
            st.session_state.student_id = None
            st.session_state.student_name = None
            st.session_state.student_email = None
            st.session_state.student_program = None
            st.rerun()
    else:
        st.info("Not logged in")
        if st.button("Login", type="primary", use_container_width=True):
            st.session_state.show_login = True
            st.rerun()
    
    st.divider()
    st.header("Admin Access")
    if st.session_state.admin_authenticated:
        st.success(f"Logged in as: {st.session_state.admin_name}")
        if st.button("View Dashboard", type="primary", use_container_width=True, key="view_dashboard_btn"):
            st.session_state.show_admin_dashboard = True
            st.rerun()
        if st.button("Logout Admin", use_container_width=True, key="admin_logout_btn"):
            st.session_state.admin_authenticated = False
            st.session_state.admin_id = None
            st.session_state.admin_name = None
            st.session_state.admin_email = None
            st.session_state.show_admin_dashboard = False
            st.rerun()
    else:
        if st.button("Admin Login", use_container_width=True, key="admin_login_sidebar_btn"):
            st.session_state.show_admin_login = True
            st.rerun()
    
    st.divider()
    st.header("Chat History")
    # Show chat history from database (not current session)
    if st.session_state.authenticated and st.session_state.get("student_id"):
        db_messages = load_recent_messages_from_db(st.session_state.student_id, limit=50)
        # Filter for user messages only, then take last 3
        user_messages = [msg for msg in db_messages if msg["role"] == "user"]
        if user_messages:
            for message in user_messages[-3:]:  # Show last 3 user messages
                content = message['content'][:50] + ('...' if len(message['content']) > 50 else '')
                st.markdown(f"""<div style="background-color:#f5f5f5;border:1px solid #000;padding:8px 12px;border-radius:18px;margin:4px 0;font-size:14px;">{content}</div>""", unsafe_allow_html=True)
        else:
            st.info("No chat history yet")
    else:
        st.info("No chat history yet")
    
    st.divider()
    st.header("Example Questions")
    example_questions = ["what are graduation requirements for MS in IT?", "What are the specializations in B.S in information technology?", "How do I apply for the applied project?"]
    for question in example_questions:
        if st.button(question, key=f"example_{question}", use_container_width=True):
            st.session_state.current_question = question
            st.rerun()
    if st.button("Show Performance Stats"):
        if rag_system.stats["total_queries"] > 0:
            st.subheader("System Statistics")
            st.metric("Total Queries", rag_system.stats["total_queries"])
            st.info("Using Gemini model")
        else:
            st.info("No queries yet")


def render_program_selection(controller, booking_ctx):
    """Render program level selection buttons (Undergraduate/BS vs Graduate/MS)"""
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🎓 Select Your Program Level")
    st.markdown("---")
    cols = st.columns(2)
    
    with cols[0]:
        st.markdown(f"""
        <div style="border:2px solid #667eea;border-radius:12px;padding:30px;margin-bottom:15px;background:white;box-shadow:0 2px 4px rgba(0,0,0,0.1);text-align:center;">
            <h4 style="margin:0 0 10px 0;color:#000;font-size:20px;">Undergraduate (BS)</h4>
            <p style="margin:0;color:#666;font-size:14px;">Bachelor's Degree Program</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Undergraduate (BS)", key="program_btn_undergraduate", use_container_width=True, type="primary"):
            result = controller.process_booking_message("undergraduate", booking_ctx)
            st.session_state.booking_context = result["booking_context"]
            
            # Check if booking is complete or cancelled
            is_final_outcome = result["state"] in ["complete", "cancelled"]
            if is_final_outcome:
                # Save final outcome summary to DB
                if result["state"] == "complete":
                    outcome_summary = "Appointment booked successfully"
                else:
                    outcome_summary = "Booking cancelled by user"
                add_chat_message("assistant", result["message"], skip_db_save=True)
                save_message_to_db(st.session_state.student_id, "assistant", outcome_summary)
            else:
                # Intermediate booking message - skip DB save
                add_chat_message("assistant", result["message"], skip_db_save=True)
            
            if result["state"] == "complete":
                st.session_state.booking_in_progress = False
                st.session_state.booking_context = None
            st.rerun()
    
    with cols[1]:
        st.markdown(f"""
        <div style="border:2px solid #667eea;border-radius:12px;padding:30px;margin-bottom:15px;background:white;box-shadow:0 2px 4px rgba(0,0,0,0.1);text-align:center;">
            <h4 style="margin:0 0 10px 0;color:#000;font-size:20px;">Graduate (MS)</h4>
            <p style="margin:0;color:#666;font-size:14px;">Master's Degree Program</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Graduate (MS)", key="program_btn_graduate", use_container_width=True, type="primary"):
            result = controller.process_booking_message("graduate", booking_ctx)
            st.session_state.booking_context = result["booking_context"]
            
            # Check if booking is complete or cancelled
            is_final_outcome = result["state"] in ["complete", "cancelled"]
            if is_final_outcome:
                # Save final outcome summary to DB
                if result["state"] == "complete":
                    outcome_summary = "Appointment booked successfully"
                else:
                    outcome_summary = "Booking cancelled by user"
                add_chat_message("assistant", result["message"], skip_db_save=True)
                save_message_to_db(st.session_state.student_id, "assistant", outcome_summary)
            else:
                # Intermediate booking message - skip DB save
                add_chat_message("assistant", result["message"], skip_db_save=True)
            
            if result["state"] == "complete":
                st.session_state.booking_in_progress = False
                st.session_state.booking_context = None
            st.rerun()


def render_advisor_selection(advisors, controller, booking_ctx):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 👤 Select an Advisor")
    st.markdown("---")
    cols = st.columns(2)
    for i, advisor in enumerate(advisors[:6]):
        col_idx = i % 2
        with cols[col_idx]:
            st.markdown(f"""
            <div style="border:2px solid #667eea;border-radius:12px;padding:20px;margin-bottom:15px;background:white;box-shadow:0 2px 4px rgba(0,0,0,0.1);">
                <h4 style="margin:0 0 10px 0;color:#000;font-size:18px;">{advisor["name"]}</h4>
                <p style="margin:0 0 8px 0;color:#666;font-size:14px;font-weight:400;">{advisor.get("title", "Advisor")}</p>
                <p style="margin:0;color:#666;font-size:13px;">{advisor["email"]}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Select {advisor['name'].split()[0]}", key=f"advisor_btn_{i}", use_container_width=True, type="primary"):
                result = controller.process_booking_message(advisor["name"], booking_ctx)
                st.session_state.booking_context = result["booking_context"]
                
                # Check if booking is complete or cancelled
                is_final_outcome = result["state"] in ["complete", "cancelled"]
                if is_final_outcome:
                    # Save final outcome summary to DB
                    if result["state"] == "complete":
                        outcome_summary = "Appointment booked successfully"
                    else:
                        outcome_summary = "Booking cancelled by user"
                    add_chat_message("assistant", result["message"], skip_db_save=True)
                    save_message_to_db(st.session_state.student_id, "assistant", outcome_summary)
                else:
                    # Intermediate booking message - skip DB save
                    add_chat_message("assistant", result["message"], skip_db_save=True)
                
                if result["state"] == "complete":
                    st.session_state.booking_in_progress = False
                    st.session_state.booking_context = None
                st.rerun()
    

def render_date_selection(suggested_dates, controller, booking_ctx):
    st.markdown("<br>", unsafe_allow_html=True)
    # Check if this is period-based selection
    is_period_selection = booking_ctx.get("date_selection_mode") == "period"
    
    if is_period_selection:
        st.markdown("### 📅 Select a Date from the Period")
    else:
        st.markdown("### 📅 Select an Alternative Date")
    st.markdown("---")
    num_cols = min(3, len(suggested_dates))
    cols = st.columns(num_cols if num_cols > 0 else 1)
    for i, alt_date in enumerate(suggested_dates[:6]):
        if alt_date and hasattr(alt_date, 'strftime'):
            col_idx = i % num_cols if num_cols > 0 else 0
            date_str = alt_date.strftime("%b %d")
            day_name = alt_date.strftime("%A")
            # Get slot count for this date if available
            available_slots = booking_ctx.get("available_slots", [])
            slot_count = len([s for s in available_slots if hasattr(s, 'date') and s.date() == alt_date])
            slot_info = f" ({slot_count} slot{'s' if slot_count > 1 else ''})" if slot_count > 0 else ""
            
            with cols[col_idx]:
                st.markdown(f"""<div style="border:1px solid #000;border-radius:10px;padding:12px;margin-bottom:10px;background:white;text-align:center;"><div style="font-weight:bold;color:#000;font-size:16px;">{day_name}</div><div style="color:#000;font-size:18px;margin:5px 0;">{date_str}</div>{f'<div style="color:#666;font-size:12px;margin-top:5px;">{slot_info}</div>' if slot_info else ''}</div>""", unsafe_allow_html=True)
                if st.button(f"Select {date_str}", key=f"date_btn_{i}", use_container_width=True, type="primary"):
                    date_input = alt_date.strftime("%B %d")
                    result = controller.process_booking_message(date_input, booking_ctx)
                    st.session_state.booking_context = result["booking_context"]
                    
                    # Check if booking is complete or cancelled
                    is_final_outcome = result["state"] in ["complete", "cancelled"]
                    if is_final_outcome:
                        # Save final outcome summary to DB
                        if result["state"] == "complete":
                            outcome_summary = "Appointment booked successfully"
                        else:
                            outcome_summary = "Booking cancelled by user"
                        add_chat_message("assistant", result["message"], skip_db_save=True)
                        save_message_to_db(st.session_state.student_id, "assistant", outcome_summary)
                    else:
                        # Intermediate booking message - skip DB save
                        add_chat_message("assistant", result["message"], skip_db_save=True)
                    
                    if result["state"] == "complete":
                        st.session_state.booking_in_progress = False
                        st.session_state.booking_context = None
                    st.rerun()


def render_time_slots(slots, controller, booking_ctx):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### ⏰ Select a Time Slot")
    st.markdown("---")
    slots_by_date = defaultdict(list)
    for slot in slots:
        slots_by_date[slot.date()].append(slot)
    for date_obj in sorted(slots_by_date.keys()):
        date_slots = sorted(slots_by_date[date_obj])
        date_str = date_obj.strftime("%A, %B %d, %Y")
        st.markdown(f"#### 📅 {date_str}")
        st.markdown("---")
        cols = st.columns(4)
        for i, slot in enumerate(date_slots[:16]):
            col_idx = i % 4
            time_str = CalendarService().format_slot_time_only(slot)
            # Create a unique key using the slot's ISO format to ensure uniqueness
            slot_key = slot.isoformat().replace(":", "_").replace("-", "_").replace(".", "_")
            button_key = f"slot_btn_{slot_key}"
            with cols[col_idx]:
                if st.button(time_str, key=button_key, use_container_width=True, type="primary"):
                    # Store the selected slot in session state to ensure we use the correct one
                    selected_slot_iso = slot.isoformat()
                    result = controller.process_booking_message(selected_slot_iso, booking_ctx)
                    st.session_state.booking_context = result["booking_context"]
                    
                    # Check if booking is complete or cancelled
                    is_final_outcome = result["state"] in ["complete", "cancelled"]
                    if is_final_outcome:
                        # Save final outcome summary to DB
                        if result["state"] == "complete":
                            outcome_summary = "Appointment booked successfully"
                        else:
                            outcome_summary = "Booking cancelled by user"
                        add_chat_message("assistant", result["message"], skip_db_save=True)
                        save_message_to_db(st.session_state.student_id, "assistant", outcome_summary)
                    else:
                        # Intermediate booking message - skip DB save
                        add_chat_message("assistant", result["message"], skip_db_save=True)
                    
                    if result["state"] == "complete":
                        st.session_state.booking_in_progress = False
                        st.session_state.booking_context = None
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)


def render_booking_options(controller):
    if not (st.session_state.booking_in_progress and st.session_state.booking_context and isinstance(st.session_state.booking_context, dict)):
        return
    booking_ctx = st.session_state.booking_context
    state = booking_ctx.get("state")
    if state == "need_program":
        render_program_selection(controller, booking_ctx)
    elif state == "need_advisor" and booking_ctx.get("available_advisors"):
        render_advisor_selection(booking_ctx["available_advisors"], controller, booking_ctx)
    elif state == "need_date" and booking_ctx.get("suggested_dates"):
        # Check if this is period-based selection (action: "show_period_dates")
        # or alternative date suggestion (action: "suggest_alternatives")
        action = booking_ctx.get("action", "")
        if action == "show_period_dates" or booking_ctx.get("date_selection_mode") == "period":
            render_date_selection(booking_ctx["suggested_dates"], controller, booking_ctx)
        elif action == "suggest_alternatives":
            render_date_selection(booking_ctx["suggested_dates"], controller, booking_ctx)
        else:
            render_date_selection(booking_ctx["suggested_dates"], controller, booking_ctx)
    elif state == "need_time" and booking_ctx.get("available_slots"):
        render_time_slots(booking_ctx["available_slots"], controller, booking_ctx)


def get_all_user_messages():
    """Get all user messages from chat history for analytics (always fresh, no caching)"""
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT id, asu_id, content, intent_category, timestamp
        FROM chat_messages
        WHERE role = 'user'
        ORDER BY timestamp DESC
        """
    ).fetchall()
    conn.close()
    return rows


def categorize_messages(messages, controller):
    """Categorize messages using IntentClassifier with hierarchical categories"""
    categorized = []
    for msg in messages:
        msg_id, asu_id, content, existing_category, timestamp = msg
        # Always re-classify to ensure correct categorization (fixes misclassified messages)
        # Re-classify to get the most up-to-date category
        intent_result = controller.intent_classifier.detect_intent(content)
        category = intent_result.get("category") or intent_result.get("intent") or "question:course_information"
        
        # Update database with the (potentially corrected) category
        if existing_category != category:
            conn = get_db_connection()
            conn.execute(
                "UPDATE chat_messages SET intent_category = ? WHERE id = ?",
                (category, msg_id)
            )
            conn.commit()
            conn.close()
        else:
            # Classify new messages with hierarchical categories
            intent_result = controller.intent_classifier.detect_intent(content)
            # Use "category" field for hierarchical format, fallback to "intent"
            category = intent_result.get("category") or intent_result["intent"]
            # Update the database with the category using message ID for precision
            conn = get_db_connection()
            conn.execute(
                "UPDATE chat_messages SET intent_category = ? WHERE id = ?",
                (category, msg_id)
            )
            conn.commit()
            conn.close()
        categorized.append({
            "asu_id": asu_id,
            "content": content,
            "category": category,
            "timestamp": timestamp
        })
    return categorized


def show_admin_dashboard():
    """Show admin dashboard with analytics"""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Admin Dashboard")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Data", use_container_width=True, key="refresh_dashboard"):
            # Force rerun to get fresh data
            st.rerun()
    
    # Show last refresh time
    import datetime
    st.caption(f"Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")
    
    # Initialize controller for intent classification
    controller = init_agent_controller()
    
    # Get all messages (always fetch fresh data - no caching)
    with st.spinner("Loading analytics..."):
        messages = get_all_user_messages()
        categorized = categorize_messages(messages, controller)
    
    if not categorized:
        st.info("No user messages found in the database.")
        return
    
    # Calculate statistics with hierarchical category parsing
    total_messages = len(categorized)
    
    # Parse hierarchical categories
    booking_count = sum(1 for m in categorized if m["category"] == "booking" or m["category"].startswith("booking"))
    question_count = sum(1 for m in categorized if m["category"] == "question" or m["category"].startswith("question:"))
    
    # Count question subcategories
    # Initialize all 4 subcategories with 0 to ensure they all show in UI
    question_subcategories = {
        "course_information": 0,
        "application_process": 0,
        "program_requirements": 0,
        "professor_information": 0
    }
    
    for m in categorized:
        category = m["category"]
        if category.startswith("question:"):
            subcategory = category.split(":", 1)[1] if ":" in category else "course_information"
            if subcategory in question_subcategories:
                question_subcategories[subcategory] = question_subcategories.get(subcategory, 0) + 1
            else:
                # Handle unknown subcategories by mapping to course_information
                question_subcategories["course_information"] += 1
        elif category == "question":
            # Handle old non-hierarchical "question" category
            question_subcategories["course_information"] += 1
    
    booking_percentage = (booking_count / total_messages * 100) if total_messages > 0 else 0
    question_percentage = (question_count / total_messages * 100) if total_messages > 0 else 0
    
    # Format subcategory names for display (define early for use in multiple places)
    subcategory_display_names = {
        "course_information": "Course Information",
        "application_process": "Application Process",
        "program_requirements": "Program Requirements",
        "professor_information": "Professor Information"
    }
    
    # Define the order for subcategories (always show all 4)
    subcategory_order = ["course_information", "application_process", "program_requirements", "professor_information"]
    
    # Get unique students count
    unique_students = len(set(m["asu_id"] for m in categorized))
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Prompts", total_messages)
    with col2:
        st.metric("Unique Students", unique_students)
    with col3:
        st.metric("Booking Requests", f"{booking_count} ({booking_percentage:.1f}%)")
    with col4:
        st.metric("Questions", f"{question_count} ({question_percentage:.1f}%)")
    
    st.markdown("---")
    
    # Category breakdown
    st.subheader("Categories Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Bar chart data
        chart_data = pd.DataFrame({
            "Category": ["Booking", "Question"],
            "Count": [booking_count, question_count],
            "Percentage": [booking_percentage, question_percentage]
        })
        
        st.bar_chart(chart_data.set_index("Category")["Count"])
    
    with col2:
        # Display percentages
        st.markdown("### Distribution")
        st.markdown(f"""
        <div style="background-color:#f0f0f0;padding:20px;border-radius:10px;">
            <h3 style="margin:0;color:#4a4a4a;">Booking Requests</h3>
            <p style="font-size:32px;margin:10px 0;color:#667eea;font-weight:bold;">{booking_percentage:.1f}%</p>
            <p style="margin:0;color:#666;">{booking_count} out of {total_messages} prompts</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background-color:#f0f0f0;padding:20px;border-radius:10px;">
            <h3 style="margin:0;color:#4a4a4a;">Questions</h3>
            <p style="font-size:32px;margin:10px 0;color:#48bb78;font-weight:bold;">{question_percentage:.1f}%</p>
            <p style="margin:0;color:#666;">{question_count} out of {total_messages} prompts</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Question subcategories breakdown (always show all 4 categories in fixed order)
    st.subheader("Question Subcategories Breakdown")
    
    # Create subcategory chart data (show all 4 categories in fixed order)
    subcat_data = []
    for subcat in subcategory_order:
        count = question_subcategories.get(subcat, 0)
        display_name = subcategory_display_names.get(subcat, subcat.replace("_", " ").title())
        percentage = (count / question_count * 100) if question_count > 0 else 0
        subcat_data.append({
            "Subcategory": display_name,
            "Count": count,
            "Percentage": percentage
        })
    
    # Display chart and distribution (only once, outside the loop)
    subcat_df = pd.DataFrame(subcat_data)
    col1, col2 = st.columns(2)
    
    with col1:
        st.bar_chart(subcat_df.set_index("Subcategory")["Count"])
    
    with col2:
        st.markdown("### Subcategory Distribution")
        for item in subcat_data:
            st.markdown(f"""
            <div style="background-color:#f0f0f0;padding:15px;border-radius:8px;margin:8px 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:bold;color:#4a4a4a;">{item['Subcategory']}</span>
                    <span style="color:#667eea;font-weight:bold;">{item['Count']} ({item['Percentage']:.1f}%)</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Recent activity
    st.subheader("Recent Activity")
    recent_messages = categorized[:20]  # Last 20 messages
    
    for msg in recent_messages:
        category = msg["category"]
        # Parse hierarchical category for display
        if category == "booking":
            category_color = "#667eea"
            category_emoji = "📅"
            category_display = "Booking"
        elif category.startswith("question:"):
            subcategory = category.split(":", 1)[1] if ":" in category else "course_information"
            category_color = "#48bb78"
            category_emoji = "❓"
            category_display = subcategory_display_names.get(subcategory, subcategory.replace("_", " ").title())
        else:
            category_color = "#48bb78"
            category_emoji = "❓"
            category_display = "Question"
        
        st.markdown(f"""
        <div style="background-color:#f9f9f9;border-left:4px solid {category_color};padding:12px;margin:8px 0;border-radius:4px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="color:{category_color};font-weight:bold;">{category_emoji} {category_display}</span>
                    <p style="margin:8px 0;color:#333;">{msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}</p>
                </div>
                <div style="text-align:right;color:#666;font-size:12px;">
                    <div>ASU ID: {msg['asu_id']}</div>
                    <div>{msg['timestamp'] if msg['timestamp'] else 'N/A'}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Category details
    st.markdown("---")
    st.subheader("Detailed Statistics")
    
    # Create tabs for booking and each question subcategory (always show all 4)
    tab_names = ["Booking Requests"] + [f"{subcategory_display_names.get(subcat, subcat.replace('_', ' ').title())}" 
                                         for subcat in subcategory_order]
    tabs = st.tabs(tab_names)
    
    with tabs[0]:
        booking_messages = [m for m in categorized if m["category"] == "booking" or m["category"].startswith("booking")]
        st.write(f"**Total Booking Requests: {len(booking_messages)}**")
        if booking_messages:
            for msg in booking_messages[:10]:
                st.text(f"• {msg['content'][:150]}")
        else:
            st.info("No booking requests found.")
    
    # Create tabs for each question subcategory (in fixed order)
    for idx, subcat in enumerate(subcategory_order, 1):
        if idx < len(tabs):
            with tabs[idx]:
                subcat_messages = [m for m in categorized 
                                 if m["category"] == f"question:{subcat}"]
                count = question_subcategories.get(subcat, 0)
                st.write(f"**Total: {count}**")
                if subcat_messages:
                    for msg in subcat_messages[:10]:
                        st.text(f"• {msg['content'][:150]}")
                else:
                    st.info(f"No {subcategory_display_names.get(subcat, subcat)} questions found yet.")


def process_user_input(input_text, controller, rag_system):
    # Check if this is a booking request (before booking starts)
    is_initial_booking_request = False
    if not st.session_state.booking_in_progress:
        student_context = None
        if st.session_state.authenticated:
            student_context = {"authenticated": True, "asu_id": st.session_state.student_id, "program_level": st.session_state.student_program}
        route_result = controller.route_request(input_text, student_context)
        is_initial_booking_request = (route_result["intent"] == "booking" and route_result["action"] == "start_booking")
    
    # Save user message to DB only if it's NOT part of an ongoing booking conversation
    # OR if it's the initial booking request (we'll save a summary instead)
    if st.session_state.booking_in_progress:
        # Skip saving intermediate booking conversation messages
        add_chat_message("user", input_text, skip_db_save=True)
    elif is_initial_booking_request:
        # Save a summary for initial booking request (skip saving the actual input text)
        add_chat_message("user", input_text, skip_db_save=True)
        save_message_to_db(st.session_state.student_id, "user", "User requested to book an appointment", "booking")
    else:
        # Normal chat message - classify and save with hierarchical category
        intent_result = controller.intent_classifier.detect_intent(input_text)
        # Use "category" field for hierarchical format (e.g., "question:program_requirements")
        # Fallback to "intent" for backward compatibility
        intent_category = intent_result.get("category") or intent_result["intent"]
        add_chat_message("user", input_text, intent_category=intent_category)
    
    if st.session_state.booking_in_progress and st.session_state.booking_context:
        with st.spinner("Processing..."):
            result = controller.process_booking_message(input_text, st.session_state.booking_context)
            st.session_state.booking_context = result["booking_context"]
            
            # Check if booking is complete or cancelled
            is_final_outcome = result["state"] in ["complete", "cancelled"]
            
            if is_final_outcome:
                # Save final outcome summary to DB
                if result["state"] == "complete":
                    outcome_summary = "Appointment booked successfully"
                else:
                    outcome_summary = "Booking cancelled by user"
                
                # Add message to chat (but save summary to DB)
                add_chat_message("assistant", result["message"], skip_db_save=True)
                save_message_to_db(st.session_state.student_id, "assistant", outcome_summary)
            else:
                # Intermediate booking message - skip DB save
                add_chat_message("assistant", result["message"], skip_db_save=True)
            
            if result["state"] in ["complete", "cancelled"]:
                st.session_state.booking_in_progress = False
                if result["state"] == "complete":
                    st.session_state.booking_context = None
            st.rerun()
    else:
        student_context = None
        if st.session_state.authenticated:
            student_context = {"authenticated": True, "asu_id": st.session_state.student_id, "program_level": st.session_state.student_program}
        route_result = controller.route_request(input_text, student_context)
        if route_result["intent"] == "booking":
            if route_result["action"] == "require_authentication":
                st.session_state.show_login = True
                add_chat_message("assistant", "Please login to book an appointment. Click the 'Login' button in the sidebar.")
                st.rerun()
            elif route_result["action"] == "start_booking":
                init_result = controller.initialize_booking_conversation(student_context["asu_id"], None)
                st.session_state.booking_context = init_result["booking_context"]
                st.session_state.booking_in_progress = True
                # Skip saving initial booking prompt to DB
                add_chat_message("assistant", init_result["message"], skip_db_save=True)
                st.rerun()
        else:
            with st.spinner("Processing your question..."):
                try:
                    start_time = time.time()
                    result = rag_system.ask(input_text)
                    response_time = time.time() - start_time
                    add_chat_message("assistant", result["answer"], sources=result.get("docs", []), time=response_time)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.info("Please try again or check your internet connection")


def main():
    st.set_page_config(page_title="IFT Academic Assistant", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")
    st.markdown(get_custom_styles(), unsafe_allow_html=True)

    init_chat_history_db()

    # Initialize systems
    rag_system = init_rag_system()
    controller = init_agent_controller()
    initialize_session_state()  # This will restore session and load history if available

    # Sidebar
    with st.sidebar:
        render_sidebar(rag_system)

    # Show admin dashboard if admin is authenticated and dashboard is requested
    if st.session_state.admin_authenticated and st.session_state.show_admin_dashboard:
        show_admin_dashboard()
        return

    # Show admin login modal if needed
    if st.session_state.show_admin_login:
        show_admin_login_modal()
        return

    # Show student login modal if needed
    if st.session_state.show_login:
        show_login_modal()
        return
    
    # Header and Book button
    col_title, col_book = st.columns([3, 1])
    with col_title:
        st.markdown("""<div style="margin-bottom:10px;"><h1 style="margin:0;color:#000;">🎓 IFT Academic Assistant</h1><p style="color:#666;margin-top:5px;font-size:16px;">Ask questions about IFT program details, courses, and academic tasks.</p></div>""", unsafe_allow_html=True)
    with col_book:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Book Appointment", type="primary", use_container_width=True):
            if st.session_state.authenticated:
                # Save initial booking request to DB
                save_message_to_db(st.session_state.student_id, "user", "User requested to book an appointment")
                
                init_result = controller.initialize_booking_conversation(st.session_state.student_id, None)
                st.session_state.booking_context = init_result["booking_context"]
                st.session_state.booking_in_progress = True
                # Skip saving initial booking prompt to DB
                add_chat_message("assistant", init_result["message"], skip_db_save=True)
                st.rerun()
            else:
                st.session_state.show_login = True
                st.rerun()
    
    st.divider()
    if st.session_state.booking_in_progress:
        st.info("🔄 **Booking in progress...** Please complete the booking conversation below.")
        st.markdown("---")
    
    # Chat messages
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            render_user_message(message)
        elif message["role"] == "assistant":
            booking_ctx = st.session_state.booking_context if st.session_state.booking_in_progress else None
            if should_show_message(message['content'], booking_ctx):
                render_assistant_message(message)

    # Booking options UI
    render_booking_options(controller)

    # if example clicked
    if "current_question" in st.session_state:
        st.session_state.chat_input_value = st.session_state.current_question
        del st.session_state.current_question
    
    # IMPORTANT: use a labeled "Send" submit so Streamlit uses accessible text (easier to target)
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([6, 1], gap="small")
        with col1:
            placeholder_text = "Continue your booking conversation..." if st.session_state.booking_in_progress else "Ask about IFT program details or book advising appointment..."
            user_input = st.text_input("Ask your question", value=st.session_state.chat_input_value, placeholder=placeholder_text, label_visibility="collapsed")
        with col2:
            # <-- Labeled 'Send' (not arrow-only). This makes it much easier to style reliably.
            send_button = st.form_submit_button("→", type="primary", use_container_width=False)
        
        if send_button and user_input.strip():
            st.session_state.chat_input_value = ""
            process_user_input(user_input.strip(), controller, rag_system)
    
    # Footer
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;color:#666;font-size:12px;'><p><strong>ASU Polytechnic School - Information Technology Program</strong></p><p>Academic Assistant</p></div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
