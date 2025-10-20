#!/usr/bin/env python3
"""
ASU IFT Academic Assistant - Main UI
Professional chat interface for ASU Information Technology program
"""

import streamlit as st
from dotenv import load_dotenv
from SimpleUnbiasedRAG import SimpleUnbiasedRAG
import time

# Initialize environment
load_dotenv()

@st.cache_resource(show_spinner=False)
def init_rag_system():
    """Initialize the RAG system"""
    with st.spinner("🔄 Loading IFT Academic Assistant..."):
        rag = SimpleUnbiasedRAG()
        success = rag.load_systems()
        if not success:
            st.error("❌ Failed to load RAG systems. Please check your API keys.")
            st.stop()
        return rag

def main():
    st.set_page_config(
        page_title="IFT Academic Assistant", 
        page_icon="🎓", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize RAG system
    rag_system = init_rag_system()
    
    # Initialize session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Sidebar - Student Information
    with st.sidebar:
        # Student Information Section
        st.header("👤 Student Information")
        
        # Student profile
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image("https://via.placeholder.com/60x60/4A90E2/FFFFFF?text=JD", width=60)
        with col2:
            st.write("**Kavya Bijja**")
            st.caption("ASU ID: 1231777770")
            st.caption("kbijja@asu.edu")
        
        # Authentication status
        st.success("✅ Authentication Successful")
        st.info("🤖 Model: llama-3.1-8b-instant")
        
        st.divider()
        
        # Chat History Section
        st.header("💬 Chat History")
        
        if st.session_state.chat_history:
            for i, message in enumerate(st.session_state.chat_history[-5:]):  # Show last 5
                if message["role"] == "user":
                    # Create chat bubble for user messages
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
        st.header("💡 Example Questions")
        
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
    # Header
    col1, col2 = st.columns([1, 8])
    with col1:
        st.image("https://via.placeholder.com/40x40/4A90E2/FFFFFF?text=🎓", width=40)
    with col2:
        st.title("IFT Academic Assistant")
        st.caption("Ask questions about IFT program details, courses, and academic tasks.")
    
    st.divider()
    
    # Chat Interface
    # Display chat history
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            # User message on the left
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
            # Assistant message on the right
            response_text = message['content']
            
            # Add evaluation info if available
            if "evaluation" in message:
                eval_info = message["evaluation"]
                winner_badge = f"🏆 {eval_info['winner'].upper()}"
                confidence_badge = f"🎯 {eval_info['confidence']}"
                
                response_text += f"\n\n---\n*{winner_badge} • {confidence_badge}*"
            
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
            
            # Show sources if available
            if "sources" in message and message["sources"]:
                with st.expander("📚 Sources"):
                    for i, source in enumerate(message["sources"][:3], 1):
                        if hasattr(source, 'page_content'):
                            snippet = source.page_content[:200] + ("..." if len(source.page_content) > 200 else "")
                            st.write(f"**Source {i}:** {snippet}")
                        else:
                            st.write(f"**Source {i}:** {str(source)[:200]}...")
    
    # Chat Input
    st.markdown("<br>", unsafe_allow_html=True)  # Add some space
    
    # Handle current question from sidebar
    if "current_question" in st.session_state:
        default_question = st.session_state.current_question
        # Clear it immediately to prevent loops
        del st.session_state.current_question
    else:
        default_question = ""
    
    # Input field and send button
    col1, col2 = st.columns([5, 1])
    
    with col1:
        user_input = st.text_input(
            "Ask your question",
            value=default_question,
            placeholder="Ask about IFT program details or book advising appointment...",
            label_visibility="collapsed"
        )
    
    with col2:
        send_button = st.button("➤", type="primary", use_container_width=True)
    
    # Process user input - only when button is clicked or Enter is pressed
    if send_button and user_input.strip():
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Generate response
        with st.spinner("🤖 AI Assistant is thinking..."):
            try:
                start_time = time.time()
                result = rag_system.ask(user_input)
                response_time = time.time() - start_time
                
                # Add assistant message to history
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "evaluation": result["evaluation"],
                    "sources": result.get("docs", []),
                    "time": response_time
                })
                
                # Rerun to show the new message
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error: {e}")
                st.info("💡 Please try again or check your internet connection")
    
    # Footer
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 12px;'>
        <p><strong>🎓 ASU Polytechnic School - Information Technology Program</strong></p>
        <p>Academic Assistant • Unbiased AI Evaluation</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Performance stats in sidebar (hidden by default, can be expanded)
    with st.sidebar:
        if st.button("📊 Show Performance Stats"):
            if rag_system.stats["total_queries"] > 0:
                st.subheader("📈 System Statistics")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Gemini Wins", rag_system.stats["gemini_wins"])
                with col2:
                    st.metric("GROQ Wins", rag_system.stats["groq_wins"])
                
                total = rag_system.stats["total_queries"]
                gemini_rate = (rag_system.stats["gemini_wins"] / total) * 100
                st.metric("Gemini Win Rate", f"{gemini_rate:.1f}%")
                st.metric("Total Queries", total)
            else:
                st.info("No queries yet")

if __name__ == "__main__":
    main()
