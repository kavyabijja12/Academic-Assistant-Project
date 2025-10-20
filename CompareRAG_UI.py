#!/usr/bin/env python3
"""
Side-by-Side Model Comparison UI
Shows Gemini vs GROQ responses simultaneously for easy comparison.
"""

import streamlit as st
from dotenv import load_dotenv
from HybridRAG import HybridRAG
import time
import asyncio
import concurrent.futures

# Initialize environment
load_dotenv()

@st.cache_resource(show_spinner=False)
def init_hybrid_rag():
    """Initialize the hybrid RAG system"""
    rag = HybridRAG()
    success = rag.load_systems()
    return rag if success else None

def run_query_parallel(rag, query, model):
    """Run query in parallel for comparison"""
    try:
        return rag.ask(query, model)
    except Exception as e:
        return {
            "answer": f"Error: {str(e)}",
            "docs": [],
            "model": model,
            "time": 0,
            "cached": False,
            "error": True
        }

def main():
    st.set_page_config(
        page_title="🎓 ASU Academic Assistant - Model Comparison", 
        page_icon="🎓", 
        layout="wide"
    )
    
    st.title("🎓 ASU Polytechnic – Academic Assistant")
    st.markdown("**🔬 Model Comparison**: See Gemini vs GROQ responses side-by-side")
    
    # Initialize RAG system
    rag = init_hybrid_rag()
    if not rag:
        st.error("Failed to load RAG systems. Please check your setup.")
        st.stop()
    
    system_info = rag.get_system_info()
    available_models = system_info["available_models"]
    
    if len(available_models) < 2:
        st.warning("⚠️ Both models are not available. Please check your API keys.")
        st.info("Available models: " + ", ".join(available_models))
        st.stop()
    
    # Sidebar for settings and stats
    with st.sidebar:
        st.header("🔧 Settings")
        
        # Auto-comparison toggle
        auto_compare = st.checkbox("🔄 Auto-compare on new queries", value=True)
        
        # Performance stats
        st.divider()
        st.header("📊 Performance Statistics")
        
        stats = rag.get_performance_stats()
        for model, data in stats.items():
            if data["total_queries"] > 0:
                with st.expander(f"{model.upper()} Stats"):
                    st.metric("Total Queries", data["total_queries"])
                    st.metric("Average Time", f"{data['average_time']}s")
                    st.metric("Cache Rate", f"{data['cache_rate']}%")
        
        # System info
        st.divider()
        st.header("🔧 System Info")
        st.success("✅ Hybrid RAG System Loaded")
        st.write(f"**Available Models:** {', '.join(available_models)}")
        if "gemini" in available_models:
            st.write(f"**Gemini Chunks:** {system_info.get('gemini_chunks', 0)}")
        if "groq" in available_models:
            st.write(f"**GROQ Chunks:** {system_info.get('groq_chunks', 0)}")
        
        # Example questions
        st.divider()
        st.header("💡 Example Questions")
        examples = [
            "What are the core IT courses?",
            "What are the graduation requirements?",
            "Which location of ASU IT course is based on?",
            "How do I apply for the IT program?",
            "What are the admission requirements?"
        ]
        
        for q in examples:
            if st.button(q, key=f"example_{q}"):
                st.session_state.current_query = q
                st.rerun()
        
        st.divider()
        if st.button("🗑️ Clear Comparison"):
            if "comparison_results" in st.session_state:
                del st.session_state.comparison_results
            st.rerun()
    
    # Initialize session state
    if "current_query" not in st.session_state:
        st.session_state.current_query = ""
    if "comparison_results" not in st.session_state:
        st.session_state.comparison_results = None
    
    # Main comparison interface
    st.header("🔬 Model Comparison")
    
    # Query input
    query = st.text_input(
        "Ask a question to compare both models:",
        value=st.session_state.current_query,
        placeholder="e.g., What are the core IT courses?"
    )
    
    # Comparison button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        compare_button = st.button("🚀 Compare Models", type="primary", use_container_width=True)
    
    # Run comparison
    if compare_button and query.strip():
        st.session_state.current_query = query
        
        with st.spinner("🔄 Running both models in parallel..."):
            # Run both models in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both queries
                gemini_future = executor.submit(run_query_parallel, rag, query, "gemini")
                groq_future = executor.submit(run_query_parallel, rag, query, "groq")
                
                # Wait for both to complete
                gemini_result = gemini_future.result()
                groq_result = groq_future.result()
        
        # Store results
        st.session_state.comparison_results = {
            "query": query,
            "gemini": gemini_result,
            "groq": groq_result,
            "timestamp": time.time()
        }
    
    # Display comparison results
    if st.session_state.comparison_results:
        results = st.session_state.comparison_results
        
        st.divider()
        st.subheader(f"📝 Query: {results['query']}")
        
        # Performance comparison
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🧠 Gemini Time", 
                f"{results['gemini']['time']:.2f}s",
                delta=None if results['gemini'].get('error') else None
            )
        
        with col2:
            st.metric(
                "⚡ GROQ Time", 
                f"{results['groq']['time']:.2f}s",
                delta=None if results['groq'].get('error') else None
            )
        
        with col3:
            speed_ratio = results['gemini']['time'] / results['groq']['time'] if results['groq']['time'] > 0 else 0
            st.metric(
                "🚀 Speed Ratio", 
                f"{speed_ratio:.1f}x",
                delta=f"{speed_ratio:.1f}x faster" if speed_ratio > 1 else f"{1/speed_ratio:.1f}x slower"
            )
        
        with col4:
            gemini_len = len(results['gemini']['answer'])
            groq_len = len(results['groq']['answer'])
            st.metric(
                "📏 Response Length", 
                f"G: {gemini_len} | G: {groq_len}",
                delta=f"{gemini_len - groq_len}" if gemini_len != groq_len else "0"
            )
        
        # Side-by-side responses
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🧠 Gemini 2.5 Flash Response")
            
            # Gemini response info
            gemini_info = results['gemini']
            if gemini_info.get('error'):
                st.error("❌ Gemini Error")
            else:
                col1a, col1b, col1c = st.columns(3)
                with col1a:
                    st.caption(f"⏱️ {gemini_info['time']:.2f}s")
                with col1b:
                    st.caption("🚀 Cached" if gemini_info['cached'] else "🔄 Fresh")
                with col1c:
                    st.caption(f"📄 {len(gemini_info['docs'])} sources")
            
            # Gemini response
            st.markdown(gemini_info['answer'])
            
            # Gemini sources
            if gemini_info.get('docs') and not gemini_info.get('error'):
                with st.expander("📚 Gemini Sources"):
                    for i, doc in enumerate(gemini_info['docs'][:3], 1):
                        if hasattr(doc, 'page_content'):
                            snippet = doc.page_content[:300] + ("..." if len(doc.page_content) > 300 else "")
                            st.write(f"**Source {i}:** {snippet}")
                        else:
                            st.write(f"**Source {i}:** {str(doc)[:300]}...")
                        st.divider()
        
        with col2:
            st.subheader("⚡ GROQ Llama 3.1 Response")
            
            # GROQ response info
            groq_info = results['groq']
            if groq_info.get('error'):
                st.error("❌ GROQ Error")
            else:
                col2a, col2b, col2c = st.columns(3)
                with col2a:
                    st.caption(f"⏱️ {groq_info['time']:.2f}s")
                with col2b:
                    st.caption("🚀 Cached" if groq_info['cached'] else "🔄 Fresh")
                with col2c:
                    st.caption(f"📄 {len(groq_info['docs'])} sources")
            
            # GROQ response
            st.markdown(groq_info['answer'])
            
            # GROQ sources
            if groq_info.get('docs') and not groq_info.get('error'):
                with st.expander("📚 GROQ Sources"):
                    for i, doc in enumerate(groq_info['docs'][:3], 1):
                        if isinstance(doc, str):
                            snippet = doc[:300] + ("..." if len(doc) > 300 else "")
                            st.write(f"**Source {i}:** {snippet}")
                        else:
                            st.write(f"**Source {i}:** {str(doc)[:300]}...")
                        st.divider()
        
        # Quality comparison
        st.divider()
        st.subheader("🎯 Quality Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🧠 Gemini 2.5 Flash**
            - ✅ More detailed and comprehensive
            - ✅ Better academic formatting
            - ✅ More nuanced understanding
            - ⚠️ Slower response time
            - ⚠️ Higher API costs
            """)
        
        with col2:
            st.markdown("""
            **⚡ GROQ Llama 3.1**
            - ✅ Much faster responses
            - ✅ Lower costs
            - ✅ Good quality for most queries
            - ⚠️ Less detailed responses
            - ⚠️ May miss some nuances
            """)
        
        # Recommendation
        st.divider()
        if speed_ratio > 2:
            st.success("💡 **Recommendation**: GROQ is significantly faster with good quality. Consider using GROQ for quick queries.")
        elif speed_ratio < 0.5:
            st.info("💡 **Recommendation**: Gemini provides more detailed responses. Consider using Gemini for complex academic queries.")
        else:
            st.info("💡 **Recommendation**: Both models perform well. Choose based on your priority: speed (GROQ) or detail (Gemini).")
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🔬 <strong>Model Comparison Tool</strong> - Compare AI models side-by-side for informed decision making</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
