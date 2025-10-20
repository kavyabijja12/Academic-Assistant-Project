#!/usr/bin/env python3
"""
ASU Academic Assistant - Main UI
A comprehensive RAG system for ASU IT program academic advising
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
    with st.spinner("🔄 Loading ASU Academic Assistant..."):
        rag = SimpleUnbiasedRAG()
        success = rag.load_systems()
        if not success:
            st.error("❌ Failed to load RAG systems. Please check your API keys.")
            st.stop()
        return rag

def main():
    st.set_page_config(
        page_title="🎓 ASU Academic Assistant", 
        page_icon="🎓", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Header
    st.title("🎓 ASU Polytechnic School")
    st.subheader("Information Technology Program - Academic Assistant")
    st.markdown("---")
    
    # Initialize RAG system
    rag_system = init_rag_system()
    
    # Sidebar
    with st.sidebar:
        st.header("📊 System Information")
        
        # System status
        st.success("✅ RAG System Active")
        st.info("🤖 **AI Models:** Gemini 2.5 Flash + GROQ Llama 3.1")
        st.info("🔍 **Search:** Hybrid (FAISS + BM25)")
        st.info("⚖️ **Evaluation:** Unbiased (Blind)")
        
        # Performance stats
        if rag_system.stats["total_queries"] > 0:
            st.subheader("📈 Performance Statistics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Gemini Wins", rag_system.stats["gemini_wins"])
            with col2:
                st.metric("GROQ Wins", rag_system.stats["groq_wins"])
            
            total = rag_system.stats["total_queries"]
            gemini_rate = (rag_system.stats["gemini_wins"] / total) * 100
            groq_rate = (rag_system.stats["groq_wins"] / total) * 100
            
            st.metric("Gemini Win Rate", f"{gemini_rate:.1f}%")
            st.metric("GROQ Win Rate", f"{groq_rate:.1f}%")
            st.metric("Total Queries", total)
        else:
            st.info("📊 No queries yet. Ask a question to see statistics!")
        
        # Quick questions
        st.subheader("💡 Quick Questions")
        quick_questions = [
            "What are the core IT courses?",
            "What are the graduation requirements?",
            "Which location is the IT program based on?",
            "How do I apply for the IT program?",
            "What are the admission requirements?",
            "Tell me about the capstone project"
        ]
        
        for question in quick_questions:
            if st.button(question, key=f"quick_{question}"):
                st.session_state.current_question = question
                st.rerun()
        
        # Clear chat
        if st.button("🗑️ Clear Chat History"):
            if "chat_history" in st.session_state:
                del st.session_state.chat_history
            st.rerun()
    
    # Main chat interface
    st.header("💬 Ask Your Question")
    
    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            if message["role"] == "assistant":
                # Show evaluation info
                if "evaluation" in message:
                    eval_info = message["evaluation"]
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.caption(f"🏆 Winner: {eval_info['winner'].upper()}")
                    with col2:
                        st.caption(f"🎯 Confidence: {eval_info['confidence']}")
                    with col3:
                        st.caption(f"⏱️ Time: {message.get('time', 0):.2f}s")
                
                # Show sources
                if "sources" in message and message["sources"]:
                    with st.expander("📚 Sources"):
                        for i, source in enumerate(message["sources"][:3], 1):
                            if hasattr(source, 'page_content'):
                                snippet = source.page_content[:300] + ("..." if len(source.page_content) > 300 else "")
                                st.write(f"**Source {i}:** {snippet}")
                            else:
                                st.write(f"**Source {i}:** {str(source)[:300]}...")
                            st.divider()
    
    # Chat input
    if "current_question" in st.session_state:
        user_input = st.text_input(
            "",
            value=st.session_state.current_question,
            placeholder="e.g., What are the core IT courses?"
        )
        # Clear the current question after using it
        del st.session_state.current_question
    else:
        user_input = st.text_input(
            "",
            placeholder="e.g., What are the core IT courses?"
        )
    
    # Send button
    if st.button("🚀 Ask AI Assistant", type="primary") and user_input:
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("🤖 AI Assistant is thinking..."):
                try:
                    start_time = time.time()
                    result = rag_system.ask(user_input)
                    response_time = time.time() - start_time
                    
                    # Display response
                    st.markdown(result["answer"])
                    
                    # Add assistant message to history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "evaluation": result["evaluation"],
                        "sources": result.get("docs", []),
                        "time": response_time
                    })
                    
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    st.info("💡 Please try again or check your internet connection")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p><strong>🎓 ASU Polytechnic School - Information Technology Program</strong></p>
        <p>Academic Assistant powered by AI • Unbiased Evaluation System</p>
        <p><em>For official academic advising, please contact your academic advisor</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
