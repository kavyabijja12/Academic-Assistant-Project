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
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
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


def save_message_to_db(asu_id: str, role: str, content: str):
    if not asu_id:
        return
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO chat_messages (asu_id, role, content) VALUES (?, ?, ?)",
        (asu_id, role, content),
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


def add_chat_message(role: str, content: str, **extras):
    message = {"role": role, "content": content}
    for key, value in extras.items():
        if value is not None:
            message[key] = value
    st.session_state.chat_history.append(message)
    if st.session_state.get("authenticated") and st.session_state.get("student_id"):
        save_message_to_db(st.session_state.student_id, role, content)


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
    """Show login modal (unchanged)"""
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


def initialize_session_state():
    defaults = {
        "chat_history": [],
        "authenticated": False,
        "show_login": False,
        "booking_context": None,
        "booking_in_progress": False,
        "chat_input_value": "",
        "history_loaded": False,
        "session_restored": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    
    # Restore session from database if not already restored
    if not st.session_state.get("session_restored"):
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
    state = booking_ctx.get("state")
    if (state == "need_advisor" and booking_ctx.get("available_advisors") and has_advisor_list) or (state == "need_time" and booking_ctx.get("available_slots") and has_time_list) or (state == "need_date" and booking_ctx.get("suggested_dates") and has_date_list):
        return False
    if (state == "need_advisor" and booking_ctx.get("available_advisors")) or (state == "need_time" and booking_ctx.get("available_slots")) or (state == "need_date" and booking_ctx.get("suggested_dates")):
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
                add_chat_message("assistant", result["message"])
                if result["state"] == "complete":
                    st.session_state.booking_in_progress = False
                    st.session_state.booking_context = None
                st.rerun()
    

def render_date_selection(suggested_dates, controller, booking_ctx):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📅 Select an Alternative Date")
    st.markdown("---")
    num_cols = min(3, len(suggested_dates))
    cols = st.columns(num_cols if num_cols > 0 else 1)
    for i, alt_date in enumerate(suggested_dates[:6]):
        if alt_date and hasattr(alt_date, 'strftime'):
            col_idx = i % num_cols if num_cols > 0 else 0
            date_str = alt_date.strftime("%b %d")
            day_name = alt_date.strftime("%A")
            with cols[col_idx]:
                st.markdown(f"""<div style="border:1px solid #000;border-radius:10px;padding:12px;margin-bottom:10px;background:white;text-align:center;"><div style="font-weight:bold;color:#000;font-size:16px;">{day_name}</div><div style="color:#000;font-size:18px;margin:5px 0;">{date_str}</div></div>""", unsafe_allow_html=True)
                if st.button(f"Select {date_str}", key=f"date_btn_{i}", use_container_width=True, type="primary"):
                    date_input = alt_date.strftime("%B %d")
                    result = controller.process_booking_message(date_input, booking_ctx)
                    st.session_state.booking_context = result["booking_context"]
                    add_chat_message("assistant", result["message"])
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
            with cols[col_idx]:
                if st.button(time_str, key=f"slot_btn_{date_obj}_{i}", use_container_width=True, type="primary"):
                    result = controller.process_booking_message(slot.isoformat(), booking_ctx)
                    st.session_state.booking_context = result["booking_context"]
                    add_chat_message("assistant", result["message"])
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
    if state == "need_advisor" and booking_ctx.get("available_advisors"):
        render_advisor_selection(booking_ctx["available_advisors"], controller, booking_ctx)
    elif state == "need_date" and booking_ctx.get("suggested_dates"):
        render_date_selection(booking_ctx["suggested_dates"], controller, booking_ctx)
    elif state == "need_time" and booking_ctx.get("available_slots"):
        render_time_slots(booking_ctx["available_slots"], controller, booking_ctx)


def process_user_input(input_text, controller, rag_system):
    add_chat_message("user", input_text)
    if st.session_state.booking_in_progress and st.session_state.booking_context:
        with st.spinner("Processing..."):
            result = controller.process_booking_message(input_text, st.session_state.booking_context)
            st.session_state.booking_context = result["booking_context"]
            add_chat_message("assistant", result["message"])
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
                add_chat_message("assistant", init_result["message"])
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

    # Show login modal if needed
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
                init_result = controller.initialize_booking_conversation(st.session_state.student_id, None)
                st.session_state.booking_context = init_result["booking_context"]
                st.session_state.booking_in_progress = True
                add_chat_message("assistant", init_result["message"])
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
